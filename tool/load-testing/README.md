# Load Testing

This directory stores load-testing scripts, notes, and result artifacts for SynCode performance benchmarking.

Planned focus areas:
- exam list DB vs Redis
- sync submit vs async submit
- polling vs WebSocket result delivery

Current entry points:
- `run-exam-list.ps1`: beginner-friendly PowerShell wrapper for the exam list benchmark
- `exam-list-db-vs-redis.js`: k6 script for `/friend/exam/semiLogin/list` and `/friend/exam/semiLogin/redis/list`
- `compare-exam-list-results.ps1`: compare two k6 summary JSON files and print a concise result table
