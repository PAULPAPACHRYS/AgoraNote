// status.js: small display helpers shared by the dashboard and the study set page.

// Human-readable labels for a study set's processing status (the badge text).
// All four working steps show as "Processing"; the detailed step is in status_message.
const LABELS = {
  queued: "Queued",
  extracting: "Processing",
  transcribing: "Processing",
  structuring: "Processing",
  generating: "Processing",
  ready: "Ready",
  failed: "Failed",
};

// The label for a status; unknown statuses are shown as they are.
export function statusLabel(status) {
  return LABELS[status] || status;
}

// A set's title, or a placeholder while the AI hasn't generated one yet.
export function setTitle(studySet) {
  return studySet.title || "Untitled study set";
}
