import assert from "node:assert/strict";

import {
  formatUtcDateTimeInZone,
  parseUtcDateTime,
  toUtcApiDateTime,
  utcDateTimeToZonedInput,
  zonedDateTimeToUtc
} from "../date-time";

assert.equal(toUtcApiDateTime("2026-09-18T09:00", "Asia/Shanghai"), "2026-09-18 01:00:00");
assert.equal(utcDateTimeToZonedInput("2026-09-18 01:00:00", "Asia/Shanghai"), "2026-09-18T09:00");
assert.equal(formatUtcDateTimeInZone("2026-09-18T01:00:00.000Z", "Asia/Shanghai"), "2026-09-18 09:00");
assert.equal(formatUtcDateTimeInZone("2026-09-18T01:00:00.000Z", "Asia/Shanghai", { includeYear: false }), "09/18 09:00");
assert.equal(parseUtcDateTime("2026-09-18 01:00:00")?.toISOString(), "2026-09-18T01:00:00.000Z");

assert.equal(toUtcApiDateTime("2026-07-01T09:00", "America/New_York"), "2026-07-01 13:00:00");
assert.equal(zonedDateTimeToUtc("2026-03-08T02:30", "America/New_York"), null, "nonexistent DST wall time must be rejected");
assert.equal(zonedDateTimeToUtc("2026-02-30T09:00", "Asia/Shanghai"), null, "invalid calendar dates must be rejected");
assert.equal(zonedDateTimeToUtc("2026-09-18T09:00", "invalid/timezone"), null);
