// status.js: small display helpers shared by the dashboard, the study set page and search.
import { t } from "./i18n.js";

// The badge text for a study set's processing status. All four working steps show as "Processing";
// the detailed step is in status_message.
const LABELS = {
  queued: "status.queued",
  extracting: "status.processing",
  transcribing: "status.processing",
  structuring: "status.processing",
  generating: "status.processing",
  ready: "status.ready",
  failed: "status.failed",
};

// The label for a status; unknown statuses are shown as they are.
export function statusLabel(status) {
  return LABELS[status] ? t(LABELS[status]) : status;
}

// A set's title, or a placeholder while the AI hasn't generated one yet.
export function setTitle(studySet) {
  return studySet.title || t("common.untitled_set");
}

// The lang attribute for a set's title: the material's language (e.g. "el"), but only for a real
// title; the placeholder above is in the interface language like the rest of the interface.
// null = no lang attribute.
export function titleLang(studySet) {
  return studySet.title ? studySet.language : null;
}
