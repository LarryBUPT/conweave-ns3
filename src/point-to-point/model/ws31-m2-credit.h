#ifndef WS31_M2_CREDIT_H
#define WS31_M2_CREDIT_H

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <limits>
#include <map>
#include <stdexcept>
#include <tuple>

namespace ns3 { namespace ws31 {

// Flow ID is the original request's generation, not a hash of its tuple.
typedef std::tuple<uint32_t, uint32_t, uint16_t, uint16_t, uint16_t, int32_t> M2Key;

// Accounts for newly admitted alternate-path payload until receiver-confirmed
// cumulative progress covers it. Missing feedback retains debt conservatively.
class M2Credit {
public:
    explicit M2Credit(uint64_t capBytes) : m_cap(capBytes) {
        if (!m_cap) throw std::invalid_argument("M2 credit cap must be positive");
    }

    void SetCapBeforeUse(uint64_t capBytes) {
        if (!capBytes || !m_highestEnd.empty() || !m_pending.empty() ||
            !m_sent.empty() || m_totalUsed)
            throw std::logic_error("M2 credit cap must be set before use");
        m_cap = capBytes;
    }

    // Call for background packets sent on the original pinned path. This makes
    // later retransmissions ineligible for a new alternate-path permit.
    void MarkPinned(const M2Key &key, uint64_t seq, uint64_t payloadBytes) {
        Advance(key, seq, payloadBytes);
    }

    // Reserves before queue admission. A refusal still records that the data
    // was seen, so a retransmission cannot gain a fresh alternate-path permit.
    bool TryReserve(const M2Key &key, uint32_t port, uint64_t uid,
                    uint64_t seq, uint64_t payloadBytes) {
        const bool fresh = Advance(key, seq, payloadBytes);
        if (!fresh) return false;
        if (m_pending.count(uid)) throw std::logic_error("M2 packet UID reused");
        const uint64_t used = Used(port);
        if (payloadBytes > m_cap || used > m_cap - payloadBytes) return false;
        Pending item;
        item.key = key;
        item.port = port;
        item.end = seq + payloadBytes;
        item.bytes = payloadBytes;
        m_pending.emplace(uid, item);
        m_used[port] = used + payloadBytes;
        m_totalUsed += payloadBytes;
        m_peakTotalUsed = std::max(m_peakTotalUsed, m_totalUsed);
        return true;
    }

    // Invoke exactly once after source-ToR queue admission. Failed admission
    // cancels the reservation; accepted data remains charged until valid ACK.
    void FinishAdmission(uint64_t uid, bool accepted) {
        auto it = m_pending.find(uid);
        if (it == m_pending.end()) throw std::logic_error("M2 admission has no reservation");
        const Pending item = it->second;
        m_pending.erase(it);
        if (!accepted) {
            Debit(item.port, item.bytes);
            return;
        }
        Committed sent;
        sent.port = item.port;
        sent.end = item.end;
        sent.bytes = item.bytes;
        auto &queue = m_sent[item.key];
        if (!queue.empty() && sent.end <= queue.back().end)
            throw std::logic_error("M2 borrowed ranges not increasing");
        queue.push_back(sent);
    }

    // Caller must verify receiver origin, original tuple, PG, and Flow ID.
    // Only fully covered intervals are released; partial ACKs are conservative.
    uint64_t Acknowledge(const M2Key &key, uint64_t cumulativeSeq) {
        auto it = m_sent.find(key);
        if (it == m_sent.end()) return 0;
        uint64_t released = 0;
        auto &queue = it->second;
        while (!queue.empty() && queue.front().end <= cumulativeSeq) {
            const Committed front = queue.front();
            queue.pop_front();
            Debit(front.port, front.bytes);
            released += front.bytes;
        }
        if (queue.empty()) m_sent.erase(it);
        return released;
    }

    uint64_t Used(uint32_t port) const {
        auto it = m_used.find(port);
        return it == m_used.end() ? 0 : it->second;
    }
    uint64_t Cap() const { return m_cap; }
    uint64_t TotalUsed() const { return m_totalUsed; }
    uint64_t PeakTotalUsed() const { return m_peakTotalUsed; }
    bool HasPending(uint64_t uid) const { return m_pending.count(uid) != 0; }
    size_t PendingCount() const { return m_pending.size(); }

private:
    struct Pending {
        M2Key key;
        uint32_t port = 0;
        uint64_t end = 0;
        uint64_t bytes = 0;
    };
    struct Committed {
        uint32_t port = 0;
        uint64_t end = 0;
        uint64_t bytes = 0;
    };

    bool Advance(const M2Key &key, uint64_t seq, uint64_t bytes) {
        if (!bytes || seq > std::numeric_limits<uint64_t>::max() - bytes)
            throw std::invalid_argument("M2 invalid payload range");
        const uint64_t end = seq + bytes;
        auto it = m_highestEnd.find(key);
        const bool fresh = it == m_highestEnd.end() || seq >= it->second;
        if (it == m_highestEnd.end()) m_highestEnd.emplace(key, end);
        else it->second = std::max(it->second, end);
        return fresh;
    }
    void Debit(uint32_t port, uint64_t bytes) {
        auto it = m_used.find(port);
        if (it == m_used.end() || it->second < bytes)
            throw std::logic_error("M2 credit underflow");
        it->second -= bytes;
        m_totalUsed -= bytes;
    }

    uint64_t m_cap;
    std::map<M2Key, uint64_t> m_highestEnd;
    std::map<uint64_t, Pending> m_pending;
    std::map<M2Key, std::deque<Committed>> m_sent;
    std::map<uint32_t, uint64_t> m_used;
    uint64_t m_totalUsed = 0;
    uint64_t m_peakTotalUsed = 0;
};

}}  // namespace ns3::ws31

#endif  // WS31_M2_CREDIT_H
