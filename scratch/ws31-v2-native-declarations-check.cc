// Portable declaration-only check. It cannot construct or launch an ns-3 network.
#include "../src/point-to-point/model/ws31-v2-native-declarations.h"
#include <fstream>
#include <iostream>

namespace {
std::string ReadFile(const std::string &path) {
    std::ifstream file(path.c_str(),std::ios::binary);
    ws31v2::Need(file.is_open(),"cannot open file");
    std::ostringstream buffer; buffer<<file.rdbuf();
    ws31v2::Need(!file.bad(),"file read failure");
    return buffer.str();
}
std::string Canonical(const ws31v2::DeclaredInput &input) {
    std::ostringstream out;
    out<<"WS31_V2_DECL_R1 K0 "<<input.family<<' '<<input.seed<<' '<<input.requests.size()
       <<' '<<input.t0<<' '<<input.horizon<<' '<<input.stop<<" 1000 48\n"
       <<"PROTOCOL_SHA256 "<<ws31v2::ProtocolSha<<'\n'
       <<"CONSTRUCTOR_SHA256 "<<ws31v2::ConstructorSha<<'\n';
    for (const auto &r:input.requests)
        out<<r.id<<' '<<r.generation<<' '<<r.source<<' '<<r.destination<<' '
           <<r.sourceIp<<' '<<r.destinationIp<<' '<<r.pg<<' '<<r.bytes<<' '
           <<r.demandNs<<' '<<r.originalTag<<' '<<unsigned(r.policyPresent)<<' '
           <<r.policyTag<<' '<<r.sport<<' '<<r.dport<<' '<<r.flowId<<'\n';
    return out.str();
}
std::string ReplaceRow(const std::string &text,size_t row,size_t column,const std::string &value) {
    std::istringstream in(text); std::ostringstream out; std::string line; size_t n=0;
    while (std::getline(in,line)) {
        if (n==row+3) {
            auto words=ws31v2::Words(line); words.at(column)=value;
            for (size_t i=0;i<words.size();++i) { if (i) out<<' '; out<<words[i]; }
            out<<'\n';
        } else out<<line<<'\n';
        ++n;
    }
    return out.str();
}
ws31v2::DeclaredInput Parse(const std::string &text) {
    std::istringstream in(text); return ws31v2::ReadDeclarations(in);
}
void Reject(const std::string &text) {
    bool rejected=false;
    try { Parse(text); } catch (const std::invalid_argument &) { rejected=true; }
    ws31v2::Need(rejected,"negative case accepted");
}
}

int main(int argc,char **argv) {
    try {
        ws31v2::Need(argc==3,"usage: --parse|--self-check|--canonical file OR --corpus cases.tsv");
        const std::string mode=argv[1];
        if (mode=="--corpus") {
            const std::string path=argv[2];
            const size_t slash=path.find_last_of("/\\");
            const std::string root=slash==std::string::npos?"":path.substr(0,slash+1);
            std::istringstream manifest(ReadFile(path)); std::string line;
            unsigned count=0;
            while (std::getline(manifest,line)) {
                const auto w=ws31v2::Words(line);
                ws31v2::Need(w.size()==4,"corpus width");
                const std::string text=ReadFile(root+w[0]);
                bool accepted=false; std::string actual;
                try { actual=Canonical(Parse(text)); accepted=true; }
                catch (const std::invalid_argument &) {}
                ws31v2::Need(w[1]=="ACCEPT" || w[1]=="REJECT","corpus expectation");
                ws31v2::Need(accepted==(w[1]=="ACCEPT"),"corpus acceptance mismatch");
                if (accepted) ws31v2::Need(actual==ReadFile(root+w[2]),"corpus field mismatch");
                std::cout<<"CASE "<<w[0]<<' '<<(accepted?"ACCEPT":"REJECT")<<'\n';
                ++count;
            }
            ws31v2::Need(count>0,"empty corpus");
            std::cout<<"WS31_V2_CORPUS_PASS cases="<<count<<" network=0 native_objects=0\n";
            return 0;
        }
        ws31v2::Need(mode=="--parse" || mode=="--self-check" || mode=="--canonical","unknown command");
        const std::string text=ReadFile(argv[2]);
        const auto input=Parse(text);
        if (mode=="--canonical") { std::cout<<Canonical(input); return 0; }
        unsigned checks=1;
        if (mode=="--self-check") {
            const std::pair<size_t,std::string> invalid[]={
                {0,"1"},{1,"1"},{4,"0"},{6,"8"},{8,"2004999999"},{9,"0"},
                {10,"2"},{11,"4294967296"},{12,"65536"},{14,"65536"},{7,"-1"},{0,"00"}};
            for (const auto &item:invalid) { Reject(ReplaceRow(text,0,item.first,item.second)); ++checks; }
            Reject(text+"\n"); ++checks;
            const size_t last=text.rfind('\n',text.size()-2);
            Reject(text.substr(0,last+1)); ++checks;
            Reject(ReplaceRow(text,0,14,"0 1")); ++checks;
            const auto original=input.requests.front().originalTag;
            const auto changed=Parse(ReplaceRow(text,0,11,original==1?"2":"1"));
            ws31v2::Need(changed.requests.front().originalTag==original &&
                         changed.requests.front().policyTag!=original,"policy/original conflated"); ++checks;
            const auto absent=Parse(ReplaceRow(ReplaceRow(text,0,10,"0"),0,11,"0"));
            ws31v2::Need(!absent.requests.front().policyPresent &&
                         absent.requests.front().originalTag==original,"absent policy/original conflated"); ++checks;
        }
        std::cout<<"WS31_V2_DECLARATION_CHECK family="<<input.family<<" requests="<<input.requests.size()
                 <<" reference_bytes="<<input.referenceWireBytes<<" checks="<<checks
                 <<" native_objects=0 label_producer=0 real_generation=0 network=0"<<std::endl;
        return 0;
    } catch (const std::exception &error) {
        std::cerr<<"WS31_V2_DECLARATION_FAILURE "<<error.what()<<std::endl;
        return 2;
    }
}
