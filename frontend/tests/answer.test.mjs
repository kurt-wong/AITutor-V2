import test from "node:test";
import assert from "node:assert/strict";
import { answerWithOptionText, isOptionCorrect } from "../src/lib/answer.ts";

const options = [
  { label: "A", text: "alpha" },
  { label: "B", text: "beta" },
  { label: "C", text: "gamma" },
  { label: "D", text: "delta" },
  { label: "E", text: "epsilon" },
  { label: "F", text: "zeta" },
  { label: "G", text: "eta" },
];

test("answerWithOptionText renders multi-answer text", () => {
  assert.equal(answerWithOptionText("BD", options), "B. beta；D. delta");
});

test("answerWithOptionText renders single-answer text", () => {
  assert.equal(answerWithOptionText("A", options), "A. alpha");
});

test("answerWithOptionText returns null for empty or missing answers", () => {
  assert.equal(answerWithOptionText(null, options), null);
  assert.equal(answerWithOptionText("", options), null);
  assert.equal(answerWithOptionText("见解析", options), null);
});

test("isOptionCorrect highlights every matched multi-answer label", () => {
  assert.equal(isOptionCorrect("B", "BD"), true);
  assert.equal(isOptionCorrect("D", "BD"), true);
  assert.equal(isOptionCorrect("A", "BD"), false);
});

test("isOptionCorrect handles empty answer and non-label text", () => {
  assert.equal(isOptionCorrect("B", null), false);
  assert.equal(isOptionCorrect("B", ""), false);
  assert.equal(isOptionCorrect("B", "见解析"), false);
});
