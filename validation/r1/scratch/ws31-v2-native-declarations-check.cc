// Portable declaration-only check. It cannot construct or launch an ns-3 network.
#include "../src/point-to-point/model/ws31-v2-native-declarations.h"
#include <fstream>
#include <iostream>

namespace {
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
        ws31v2::Need(argc==3,"usage: --parse|--self-check requests.native");
        const std::string mode=argv[1];
        ws31v2::Need(mode=="--parse" || mode=="--self-check","unknown command");
        std::ifstream file(argv[2]); ws31v2::Need(file.is_open(),"cannot open declaration");
        std::ostringstream buffer; buffer<<file.rdbuf();
        ws31v2::Need(!file.bad(),"file read failure");
        const std::string text=buffer.str();
        const auto input=Parse(text);
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
