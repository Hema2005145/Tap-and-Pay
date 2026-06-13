// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract AuditTrail {
    struct LogEntry {
        uint256 timestamp;
        uint256 clientId;
        uint256 amountCents;
        string status;
    }

    // Mapping from a SHA-256 Transaction Hash to its LogEntry
    mapping(string => LogEntry) public auditLogs;

    event TransactionLogged(string txHash, uint256 clientId, string status);

    function logTransaction(string memory _txHash, uint256 _clientId, uint256 _amountCents, string memory _status) public {
        require(auditLogs[_txHash].timestamp == 0, "Transaction hash already exists");
        
        auditLogs[_txHash] = LogEntry({
            timestamp: block.timestamp,
            clientId: _clientId,
            amountCents: _amountCents,
            status: _status
        });

        emit TransactionLogged(_txHash, _clientId, _status);
    }

    function getTransaction(string memory _txHash) public view returns (uint256, uint256, uint256, string memory) {
        LogEntry memory entry = auditLogs[_txHash];
        require(entry.timestamp != 0, "Transaction hash not found");
        return (entry.timestamp, entry.clientId, entry.amountCents, entry.status);
    }
}
