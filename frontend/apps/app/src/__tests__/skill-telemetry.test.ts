import assert from "node:assert/strict";

import {
  parseSseEvent,
  splitSseFrames,
  toSkillTelemetryEvent
} from "../lib/skill-telemetry";

function main() {
  const chunk = [
    "event: tool.started\n",
    "id: evt-1\n",
    "data: {\"tool\":\"get_question\",\"preview\":\"101\"}\n\n",
    "event: tool.started\n",
    "id: evt-2\n",
    "data: {\"tool\":\"skill_view\",\"preview\":\"syncode-diagnosis\"}\n\n",
    "event: run.completed\n",
    "data: {\"output\":\"not collected\"}"
  ].join("");
  const split = splitSseFrames(chunk);
  assert.equal(split.frames.length, 2);

  const nonSkill = parseSseEvent(split.frames[0]);
  assert.ok(nonSkill);
  assert.equal(toSkillTelemetryEvent(nonSkill, "run-1", 0), undefined);

  const parsedSkill = parseSseEvent(split.frames[1]);
  assert.ok(parsedSkill);
  const skillEvent = toSkillTelemetryEvent(parsedSkill, "run-1", 1);
  assert.ok(skillEvent);
  assert.equal(skillEvent.event_id, "run-1:evt-2");
  assert.equal(skillEvent.event_type, "skill.invoked");
  assert.equal(skillEvent.skill_name, "syncode-diagnosis");
  assert.deepEqual(skillEvent.payload, { tool: "skill_view" });

  assert.equal(parseSseEvent(split.rest), null);

  const parsedUnderscoreSkill = parseSseEvent(
    'event: tool.started\ndata: {"tool":"skill_view","preview":"personal_debugger"}'
  );
  assert.ok(parsedUnderscoreSkill);
  assert.equal(
    toSkillTelemetryEvent(parsedUnderscoreSkill, "run-1", 2)?.skill_name,
    "personal_debugger"
  );
}

main();
