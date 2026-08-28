export interface AnswerOption {
  label: string;
  text: string;
}

export function answerWithOptionText(
  answer?: string | null,
  options?: AnswerOption[] | null,
): string | null {
  const answerLabels = new Set(
    (answer ?? "")
      .trim()
      .toUpperCase()
      .split("")
      .filter((ch) => /^[A-Z]$/.test(ch)),
  );
  const matched = (options ?? []).filter((option) =>
    answerLabels.has(option.label.trim().toUpperCase()),
  );
  if (matched.length === 0) return null;
  return matched.map((option) => `${option.label}. ${option.text}`).join("；");
}

export function isOptionCorrect(label: string, answer?: string | null): boolean {
  const normalizedLabel = label.trim().toUpperCase();
  return (answer ?? "")
    .trim()
    .toUpperCase()
    .split("")
    .some((ch) => ch === normalizedLabel && /^[A-Z]$/.test(ch));
}
