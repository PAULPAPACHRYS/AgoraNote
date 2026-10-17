// Human-readable labels for a study set's processing status.
const LABELS = {
  queued: "Queued",
  extracting: "Processing",
  transcribing: "Processing",
  structuring: "Processing",
  generating: "Processing",
  ready: "Ready",
  failed: "Failed",
};

export function statusLabel(status) {
  return LABELS[status] || status;
}

export function setTitle(studySet) {
  return studySet.title || "Untitled study set";
}
