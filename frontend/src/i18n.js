// i18n.js ("internationalisation"): every text of the interface, in English and Greek.
//
// Components show a text with t(key), e.g. t("nav.search") or t("flashcards.card", { n: 2, total: 9 })
// for "Card 2 of 9". The language is chosen with the language button in the header and saved with the
// display settings (display.js). Switching reloads the page, so the language never changes while a
// page is open: t() can simply look up the text whenever a component is drawn.
//
// The generated study material is not translated: it stays in the lecture's own language.
// Messages from the server (progress, errors) arrive as a code plus values and are translated by
// messageText() below; their texts are the "message." keys (see backend/app/messages.py).
import { cloneElement, isValidElement } from "react";

import { loadDisplay } from "./display.js";

// The interface language of this visit: "en" or "el".
export const language = loadDisplay().language;

// {name} in a text is replaced by values.name. A number is written the local way (500,000 in English,
// 500.000 in Greek). Plurals: when values.count is 1, the key's "_one" text is used if there is one
// ("1 point" instead of "1 points").
// A value can also be a React element, e.g. t("quiz.unlocked", { title: <strong>...</strong> }); then
// t() returns a list of strings and elements, which React draws like any other content.
export function t(key, values = {}) {
  const texts = TEXTS[language];
  let text = texts[key] ?? TEXTS.en[key] ?? key; // a missing Greek text falls back to the English one
  if (values.count === 1 && texts[`${key}_one`]) text = texts[`${key}_one`];

  // split() with a capture group keeps the placeholder names at the odd positions:
  // "Card {n} of {total}" -> ["Card ", "n", " of ", "total", ""]
  const parts = text.split(/\{(\w+)\}/).map((part, i) => {
    if (i % 2 === 0) return part;
    const value = values[part];
    if (value === undefined) return `{${part}}`; // a forgotten value stays visible
    return typeof value === "number" ? value.toLocaleString(language) : value;
  });
  if (parts.every((part) => typeof part === "string")) return parts.join("");
  // React needs a key on each element in a list
  return parts.map((part, i) => (isValidElement(part) ? cloneElement(part, { key: i }) : part));
}

// A message from the server ({code, values}) in the interface language. Unknown codes (e.g. from a
// newer server) get a general "something went wrong".
export function messageText(message) {
  const key = `message.${message.code}`;
  return key in TEXTS.en ? t(key, message.values) : t("message.unknown");
}

// A date the local way, e.g. 19/11/2026 in Greek.
export function formatDate(value) {
  return new Date(value).toLocaleDateString(language);
}

// A date and time the local way, e.g. "20 Nov 2026, 14:32" ("20 Νοε 2026, 14:32" in Greek).
export function formatDateTime(value) {
  return new Date(value).toLocaleString(language, { dateStyle: "medium", timeStyle: "short" });
}

const TEXTS = {
  en: {
    // shared
    "common.loading": "Loading…",
    "common.cancel": "Cancel",
    "common.back_to_sets": "Back to your study sets",
    "common.untitled_set": "Untitled study set",
    "common.chapters": "Chapters",
    "common.new_set": "New study set",

    // header and footer
    "nav.search": "Search your study sets",
    "nav.privacy": "Privacy",
    "nav.language": "Language",

    // welcome (signed out, and the dashboard without study sets)
    "welcome.title": "Welcome to AgoraNote",
    "welcome.intro":
      "Upload lecture notes or a lecture recording, or paste some text. AgoraNote splits it into chapters and writes a summary, key concepts, practice questions and study aids for each one.",
    "welcome.quizzes_short": "Then test yourself with chapter quizzes and unlock the next chapter.",
    "welcome.quizzes":
      "Then test yourself with chapter quizzes: correct answers earn points, and enough points unlock the next chapter's quiz.",
    "welcome.sign_in": "Sign in",
    "welcome.sign_up": "Create an account",
    "welcome.first_set": "Create your first study set",

    // display settings
    "display.button": "Display settings",
    "display.reset": "Reset to defaults",
    "display.done": "Done",
    "display.save_error": "Couldn't save to your account. The settings are still saved in this browser.",
    "display.theme": "Theme",
    "display.theme.system": "Same as my device",
    "display.theme.light": "Light",
    "display.theme.dark": "Dark",
    "display.theme.contrast": "High contrast",
    "display.text_size": "Text size",
    "display.text_size.small": "Small",
    "display.text_size.normal": "Normal",
    "display.text_size.large": "Large",
    "display.text_size.larger": "Extra large",
    "display.line_spacing": "Line spacing",
    "display.line_spacing.normal": "Normal",
    "display.line_spacing.relaxed": "Relaxed",
    "display.line_spacing.wide": "Wide",
    "display.text_spacing": "Letter and word spacing",
    "display.text_spacing.normal": "Normal",
    "display.text_spacing.wider": "Wider",
    "display.text_spacing.widest": "Widest",
    "display.reading_width": "Reading width",
    "display.reading_width.narrow": "Narrow",
    "display.reading_width.normal": "Normal",
    "display.reading_width.wide": "Wide",
    "display.reduce_motion": "Reduce motion",
    "display.reduce_motion.system": "Same as my device",
    "display.reduce_motion.on": "On",
    "display.reduce_motion.off": "Off",
    "display.underline_links": "Underline all links",
    "display.underline_links.off": "Off",
    "display.underline_links.on": "On",

    // study set statuses (the badges)
    "status.queued": "Queued",
    "status.processing": "Processing",
    "status.ready": "Ready",
    "status.failed": "Failed",

    // dashboard
    "dashboard.title": "Your study sets",
    "dashboard.progress": "Progress",

    // new study set
    "new.title_label": "Title (optional)",
    "new.title_placeholder": "Leave empty to generate one from the material",
    "new.files": "Files",
    "new.files_help":
      "Text: .txt, .md, .pdf, .docx · Audio/video: .mp3, .m4a, .wav, .ogg, .webm, .mp4 · Up to {max} files, {max_mb} MB each.",
    "new.text": "…and/or paste text",
    "new.uploading": "Uploading…",
    "new.create": "Create study set",
    "new.limit_left": "You can create {count} more study sets right now (the limit is {max} in 24 hours).",
    "new.limit_left_one": "You can create 1 more study set right now (the limit is {max} in 24 hours).",
    "new.limit_reached_title": "Daily limit reached",
    "new.limit_reached":
      "You have created {max} study sets in the last 24 hours, the most allowed. You can create the next one from {time}.",

    // study set page
    "set.back": "← Your study sets",
    "set.waiting": "Waiting to start…",
    "set.failed": "Processing failed.",
    "set.retry": "Retry",
    "set.retrying": "Retrying…",
    "set.overall_progress": "Overall progress",
    "set.points": "{earned} / {total} points",
    "set.delete": "Delete study set",
    "set.delete_confirm": "Delete this study set, its chapters and its uploaded files? This can't be undone.",
    "set.delete_yes": "Yes, delete",
    "set.deleting": "Deleting…",

    // chapter list and chapter page
    "chapter.points_label": "Chapter {n} points",
    "chapter.points_short": "{earned} / {max} pts",
    "chapter.unlock_hint": "Earn {count} more points in Chapter {chapter} to unlock this quiz.",
    "chapter.unlock_hint_one": "Earn 1 more point in Chapter {chapter} to unlock this quiz.",
    "chapter.complete": "✓ Chapter complete",
    "chapter.of": "Chapter {n} of {total}",
    "chapter.tabs": "Chapter materials",
    "chapter.tab.summary": "Summary",
    "chapter.tab.concepts": "Key concepts",
    "chapter.tab.practice": "Q&A practice",
    "chapter.tab.aids": "Study aids",
    "chapter.tab.quiz": "Quiz",
    "chapter.tab.source": "Source",
    "chapter.source_intro": "The part of your material this chapter was made from.",
    "chapter.locked": "This quiz is locked",
    "chapter.locked_other_tabs": "The study materials in the other tabs are always open.",
    "chapter.locked_link": "Go to the Chapter {n} quiz →",
    "chapter.outline": "Outline",
    "chapter.checklist": "Review checklist",
    "chapter.memory_tips": "Memory tips",

    // flashcards
    "flashcards.none": "No practice questions for this chapter.",
    "flashcards.question": "Question",
    "flashcards.answer": "Answer",
    "flashcards.hint_reveal": "Click or press Space to reveal the answer",
    "flashcards.hint_back": "Click or press Space to see the question",
    "flashcards.previous": "← Previous",
    "flashcards.next": "Next →",
    "flashcards.card": "Card {n} of {total}",

    // quiz
    "quiz.loading": "Loading quiz…",
    "quiz.chapter_points": "Chapter points",
    "quiz.chapter_points_value": "Chapter points: {earned} / {max}",
    "quiz.unlock_at": "Unlock next chapter at {n} pts",
    "quiz.all_chapters": "All chapters: {earned} / {total} points · {percent}%",
    "quiz.unlocked": "You unlocked the quiz of {title}!",
    "quiz.unlocked_link": "Go to that quiz →",
    "quiz.topic": "Topic: {name} · {count} points",
    "quiz.topic_one": "Topic: {name} · 1 point",
    "quiz.correct": "Correct! +{count} points",
    "quiz.correct_one": "Correct! +1 point",
    "quiz.wrong": "Not quite — the right answer is highlighted.",
    "quiz.replacement": "A new question on {topic} is being prepared.",
    "quiz.next_question": "Next question",
    "quiz.preparing": "Preparing your next question…",
    "quiz.complete": "Chapter complete!",
    "quiz.mastered": "You mastered every topic in this chapter.",
    "quiz.next_chapter": "Next chapter: {title} →",
    "quiz.back_to_set": "Back to the study set",

    // search
    "search.title": "Search",
    "search.empty": "Type a word or phrase in the search box to search all your study sets.",
    "search.results": "Results for “{q}”",
    "search.searching": "Searching…",
    "search.nothing":
      "No study sets or chapters match “{q}”. Try a different word, or check the spelling (accents count in Greek).",
    "search.home": "Back to home screen",
    "search.sets": "Study sets",
    "search.chapter": "Chapter {n}: {title}",

    // not found and error pages
    "notfound.title": "Page not found",
    "notfound.text": "There is no page at {path}. The link may be mistyped, or the page may have been moved or deleted.",
    "error.title": "Something went wrong",
    "error.text":
      "Sorry, this page ran into a problem and couldn't be shown. Your study sets and points are safe: they are stored on the server. Try loading the page again, or go back to your study sets.",
    "error.try_again": "Try again",
    "error.details": "Error details (development only)",
    "error.no_server": "Could not reach the server. Is the API running?",
    "error.request_failed": "Request failed ({status})",

    // messages from the server (see backend/app/messages.py): progress
    "message.reading_files": "Reading your files",
    "message.transcribing": "Transcribing recording {recording} of {total}",
    "message.transcribing_part": "Transcribing recording {recording} of {total} (part {part} of {parts})",
    "message.finding_chapters": "Finding the chapters",
    "message.generating_chapter": "Generating chapter {position} of {total}",
    "message.retrying": "The AI service had a hiccup, retrying…",
    // why processing failed
    "message.processing_failed": "Something went wrong while processing this study set. Please try again.",
    "message.ai_unreachable": "The AI service could not be reached or took too long to answer. Please try again later.",
    "message.transcription_unreachable":
      "The transcription service could not be reached or took too long to answer. Please try again later.",
    "message.start_failed": "Processing could not be started. Please try again.",
    "message.not_text_document": "“{filename}” is not a text document.",
    "message.pdf_password": "“{filename}” is password-protected. Please upload an unprotected PDF.",
    "message.pdf_unreadable": "“{filename}” could not be read. Is it a valid PDF?",
    "message.pdf_scanned": "“{filename}” looks like scanned images; only text-based PDFs are supported for now.",
    "message.file_unreadable": "“{filename}” could not be read.",
    "message.audio_unreadable": "“{filename}” could not be read as audio or video (is there a sound track?).",
    "message.no_speech": "No speech was found in “{filename}”.",
    "message.material_too_long":
      "The material is too long ({length} characters; the limit is {max}). Try splitting it into several study sets.",
    "message.not_enough_material": "Not enough material to build a study set.",
    // API errors
    "message.study_set_not_found": "Study set not found.",
    "message.chapter_not_found": "Chapter not found.",
    "message.question_not_found": "Question not found.",
    "message.quiz_locked": "Earn {count} more points in Chapter {chapter} to unlock this quiz.",
    "message.quiz_locked_one": "Earn 1 more point in Chapter {chapter} to unlock this quiz.",
    "message.already_answered": "This question has already been answered.",
    "message.unsupported_type": "“{filename}” has an unsupported type. Allowed: {allowed}.",
    "message.file_empty": "“{filename}” is empty.",
    "message.file_too_large": "“{filename}” is larger than {max_mb} MB.",
    "message.nothing_uploaded": "Choose at least one file or paste some text.",
    "message.too_many_files": "You can upload at most {max} files.",
    "message.text_too_long": "Pasted text is too long (max {max} characters).",
    "message.title_too_long": "Title is too long (max {max} characters).",
    "message.daily_limit_reached": "You can create at most {max} study sets in 24 hours.",
    "message.only_failed_retry": "Only a failed study set can be retried.",
    "message.sign_in_required": "Please sign in.",
    "message.session_expired": "Your session has expired. Please sign in again.",
    "message.sign_in_unreachable": "The sign-in service can't be reached. Please try again.",
    "message.unknown": "Something went wrong. Please try again.",
  },

  el: {
    "common.loading": "Φόρτωση…",
    "common.cancel": "Ακύρωση",
    "common.back_to_sets": "Πίσω στα σετ μελέτης σας",
    "common.untitled_set": "Σετ μελέτης χωρίς τίτλο",
    "common.chapters": "Κεφάλαια",
    "common.new_set": "Νέο σετ μελέτης",

    "nav.search": "Αναζήτηση στα σετ μελέτης σας",
    "nav.privacy": "Απόρρητο",
    "nav.language": "Γλώσσα",

    "welcome.title": "Καλώς ήρθατε στο AgoraNote",
    "welcome.intro":
      "Ανεβάστε σημειώσεις ή ηχογράφηση μιας διάλεξης, ή επικολλήστε κείμενο. Το AgoraNote το χωρίζει σε κεφάλαια και γράφει για το καθένα περίληψη, βασικές έννοιες, ερωτήσεις εξάσκησης και βοηθήματα μελέτης.",
    "welcome.quizzes_short": "Έπειτα εξεταστείτε με τα κουίζ των κεφαλαίων και ξεκλειδώστε το επόμενο κεφάλαιο.",
    "welcome.quizzes":
      "Έπειτα εξεταστείτε με τα κουίζ των κεφαλαίων: οι σωστές απαντήσεις δίνουν πόντους, και με αρκετούς πόντους ξεκλειδώνει το κουίζ του επόμενου κεφαλαίου.",
    "welcome.sign_in": "Σύνδεση",
    "welcome.sign_up": "Δημιουργία λογαριασμού",
    "welcome.first_set": "Δημιουργήστε το πρώτο σας σετ μελέτης",

    "display.button": "Ρυθμίσεις εμφάνισης",
    "display.reset": "Επαναφορά προεπιλογών",
    "display.done": "Τέλος",
    "display.save_error":
      "Δεν ήταν δυνατή η αποθήκευση στον λογαριασμό σας. Οι ρυθμίσεις παραμένουν αποθηκευμένες σε αυτό το πρόγραμμα περιήγησης.",
    "display.theme": "Θέμα",
    "display.theme.system": "Όπως η συσκευή μου",
    "display.theme.light": "Φωτεινό",
    "display.theme.dark": "Σκοτεινό",
    "display.theme.contrast": "Υψηλή αντίθεση",
    "display.text_size": "Μέγεθος κειμένου",
    "display.text_size.small": "Μικρό",
    "display.text_size.normal": "Κανονικό",
    "display.text_size.large": "Μεγάλο",
    "display.text_size.larger": "Πολύ μεγάλο",
    "display.line_spacing": "Διάστιχο",
    "display.line_spacing.normal": "Κανονικό",
    "display.line_spacing.relaxed": "Άνετο",
    "display.line_spacing.wide": "Ευρύ",
    "display.text_spacing": "Απόσταση γραμμάτων και λέξεων",
    "display.text_spacing.normal": "Κανονική",
    "display.text_spacing.wider": "Μεγαλύτερη",
    "display.text_spacing.widest": "Μέγιστη",
    "display.reading_width": "Πλάτος ανάγνωσης",
    "display.reading_width.narrow": "Στενό",
    "display.reading_width.normal": "Κανονικό",
    "display.reading_width.wide": "Φαρδύ",
    "display.reduce_motion": "Μείωση κίνησης",
    "display.reduce_motion.system": "Όπως η συσκευή μου",
    "display.reduce_motion.on": "Ναι",
    "display.reduce_motion.off": "Όχι",
    "display.underline_links": "Υπογράμμιση όλων των συνδέσμων",
    "display.underline_links.off": "Όχι",
    "display.underline_links.on": "Ναι",

    "status.queued": "Σε αναμονή",
    "status.processing": "Σε επεξεργασία",
    "status.ready": "Έτοιμο",
    "status.failed": "Απέτυχε",

    "dashboard.title": "Τα σετ μελέτης σας",
    "dashboard.progress": "Πρόοδος",

    "new.title_label": "Τίτλος (προαιρετικός)",
    "new.title_placeholder": "Αφήστε το κενό για να δημιουργηθεί από το υλικό",
    "new.files": "Αρχεία",
    "new.files_help":
      "Κείμενο: .txt, .md, .pdf, .docx · Ήχος/βίντεο: .mp3, .m4a, .wav, .ogg, .webm, .mp4 · Έως {max} αρχεία, {max_mb} MB το καθένα.",
    "new.text": "…ή/και επικολλήστε κείμενο",
    "new.uploading": "Ανέβασμα…",
    "new.create": "Δημιουργία σετ μελέτης",
    "new.limit_left": "Μπορείτε να δημιουργήσετε ακόμη {count} σετ μελέτης τώρα (το όριο είναι {max} σε 24 ώρες).",
    "new.limit_reached_title": "Συμπληρώθηκε το ημερήσιο όριο",
    "new.limit_reached":
      "Δημιουργήσατε {max} σετ μελέτης τις τελευταίες 24 ώρες, το μέγιστο επιτρεπτό. Μπορείτε να δημιουργήσετε το επόμενο από {time}.",

    "set.back": "← Τα σετ μελέτης σας",
    "set.waiting": "Αναμονή για έναρξη…",
    "set.failed": "Η επεξεργασία απέτυχε.",
    "set.retry": "Δοκιμή ξανά",
    "set.retrying": "Νέα προσπάθεια…",
    "set.overall_progress": "Συνολική πρόοδος",
    "set.points": "{earned} / {total} πόντοι",
    "set.delete": "Διαγραφή σετ μελέτης",
    "set.delete_confirm":
      "Να διαγραφεί αυτό το σετ μελέτης, τα κεφάλαιά του και τα αρχεία που ανεβάσατε; Η ενέργεια δεν αναιρείται.",
    "set.delete_yes": "Ναι, διαγραφή",
    "set.deleting": "Διαγραφή…",

    "chapter.points_label": "Πόντοι κεφαλαίου {n}",
    "chapter.points_short": "{earned} / {max} πόντοι",
    "chapter.unlock_hint": "Κερδίστε {count} ακόμη πόντους στο Κεφάλαιο {chapter} για να ξεκλειδώσετε αυτό το κουίζ.",
    "chapter.unlock_hint_one": "Κερδίστε 1 ακόμη πόντο στο Κεφάλαιο {chapter} για να ξεκλειδώσετε αυτό το κουίζ.",
    "chapter.complete": "✓ Το κεφάλαιο ολοκληρώθηκε",
    "chapter.of": "Κεφάλαιο {n} από {total}",
    "chapter.tabs": "Υλικό κεφαλαίου",
    "chapter.tab.summary": "Περίληψη",
    "chapter.tab.concepts": "Βασικές έννοιες",
    "chapter.tab.practice": "Ερωτήσεις εξάσκησης",
    "chapter.tab.aids": "Βοηθήματα μελέτης",
    "chapter.tab.quiz": "Κουίζ",
    "chapter.tab.source": "Αρχικό κείμενο",
    "chapter.source_intro": "Το τμήμα του υλικού σας από το οποίο δημιουργήθηκε αυτό το κεφάλαιο.",
    "chapter.locked": "Αυτό το κουίζ είναι κλειδωμένο",
    "chapter.locked_other_tabs": "Το υλικό μελέτης στις άλλες καρτέλες είναι πάντα διαθέσιμο.",
    "chapter.locked_link": "Μετάβαση στο κουίζ του Κεφαλαίου {n} →",
    "chapter.outline": "Διάγραμμα",
    "chapter.checklist": "Λίστα επανάληψης",
    "chapter.memory_tips": "Συμβουλές απομνημόνευσης",

    "flashcards.none": "Δεν υπάρχουν ερωτήσεις εξάσκησης για αυτό το κεφάλαιο.",
    "flashcards.question": "Ερώτηση",
    "flashcards.answer": "Απάντηση",
    "flashcards.hint_reveal": "Κάντε κλικ ή πατήστε Space για να δείτε την απάντηση",
    "flashcards.hint_back": "Κάντε κλικ ή πατήστε Space για να δείτε την ερώτηση",
    "flashcards.previous": "← Προηγούμενη",
    "flashcards.next": "Επόμενη →",
    "flashcards.card": "Κάρτα {n} από {total}",

    "quiz.loading": "Φόρτωση κουίζ…",
    "quiz.chapter_points": "Πόντοι κεφαλαίου",
    "quiz.chapter_points_value": "Πόντοι κεφαλαίου: {earned} / {max}",
    "quiz.unlock_at": "Το επόμενο κεφάλαιο ξεκλειδώνει στους {n} πόντους",
    "quiz.all_chapters": "Όλα τα κεφάλαια: {earned} / {total} πόντοι · {percent}%",
    "quiz.unlocked": "Ξεκλειδώσατε το κουίζ του κεφαλαίου {title}!",
    "quiz.unlocked_link": "Μετάβαση σε αυτό το κουίζ →",
    "quiz.topic": "Θέμα: {name} · {count} πόντοι",
    "quiz.topic_one": "Θέμα: {name} · 1 πόντος",
    "quiz.correct": "Σωστά! +{count} πόντοι",
    "quiz.correct_one": "Σωστά! +1 πόντος",
    "quiz.wrong": "Όχι ακριβώς — η σωστή απάντηση είναι επισημασμένη.",
    "quiz.replacement": "Ετοιμάζεται νέα ερώτηση για το θέμα {topic}.",
    "quiz.next_question": "Επόμενη ερώτηση",
    "quiz.preparing": "Ετοιμάζεται η επόμενη ερώτησή σας…",
    "quiz.complete": "Το κεφάλαιο ολοκληρώθηκε!",
    "quiz.mastered": "Κατακτήσατε όλα τα θέματα αυτού του κεφαλαίου.",
    "quiz.next_chapter": "Επόμενο κεφάλαιο: {title} →",
    "quiz.back_to_set": "Πίσω στο σετ μελέτης",

    "search.title": "Αναζήτηση",
    "search.empty": "Γράψτε μια λέξη ή φράση στο πλαίσιο αναζήτησης για να ψάξετε σε όλα τα σετ μελέτης σας.",
    "search.results": "Αποτελέσματα για «{q}»",
    "search.searching": "Αναζήτηση…",
    "search.nothing":
      "Κανένα σετ μελέτης ή κεφάλαιο δεν ταιριάζει με «{q}». Δοκιμάστε άλλη λέξη ή ελέγξτε την ορθογραφία (οι τόνοι μετράνε).",
    "search.home": "Πίσω στην αρχική",
    "search.sets": "Σετ μελέτης",
    "search.chapter": "Κεφάλαιο {n}: {title}",

    "notfound.title": "Η σελίδα δεν βρέθηκε",
    "notfound.text":
      "Δεν υπάρχει σελίδα στη διεύθυνση {path}. Ο σύνδεσμος μπορεί να είναι λάθος, ή η σελίδα να έχει μετακινηθεί ή διαγραφεί.",
    "error.title": "Κάτι πήγε στραβά",
    "error.text":
      "Λυπούμαστε, παρουσιάστηκε πρόβλημα και η σελίδα δεν μπόρεσε να εμφανιστεί. Τα σετ μελέτης και οι πόντοι σας είναι ασφαλή: αποθηκεύονται στον διακομιστή. Δοκιμάστε να φορτώσετε ξανά τη σελίδα ή επιστρέψτε στα σετ μελέτης σας.",
    "error.try_again": "Δοκιμή ξανά",
    "error.details": "Λεπτομέρειες σφάλματος (μόνο κατά την ανάπτυξη)",
    "error.no_server": "Δεν ήταν δυνατή η σύνδεση με τον διακομιστή. Λειτουργεί το API;",
    "error.request_failed": "Το αίτημα απέτυχε ({status})",

    "message.reading_files": "Ανάγνωση των αρχείων σας",
    "message.transcribing": "Απομαγνητοφώνηση ηχογράφησης {recording} από {total}",
    "message.transcribing_part": "Απομαγνητοφώνηση ηχογράφησης {recording} από {total} (τμήμα {part} από {parts})",
    "message.finding_chapters": "Εντοπισμός των κεφαλαίων",
    "message.generating_chapter": "Δημιουργία κεφαλαίου {position} από {total}",
    "message.retrying": "Η υπηρεσία AI είχε ένα προσωρινό πρόβλημα, γίνεται νέα προσπάθεια…",
    "message.processing_failed": "Κάτι πήγε στραβά κατά την επεξεργασία αυτού του σετ μελέτης. Δοκιμάστε ξανά.",
    "message.ai_unreachable":
      "Η υπηρεσία AI δεν ήταν διαθέσιμη ή άργησε πολύ να απαντήσει. Δοκιμάστε ξανά αργότερα.",
    "message.transcription_unreachable":
      "Η υπηρεσία απομαγνητοφώνησης δεν ήταν διαθέσιμη ή άργησε πολύ να απαντήσει. Δοκιμάστε ξανά αργότερα.",
    "message.start_failed": "Δεν ήταν δυνατή η έναρξη της επεξεργασίας. Δοκιμάστε ξανά.",
    "message.not_text_document": "Το «{filename}» δεν είναι έγγραφο κειμένου.",
    "message.pdf_password": "Το «{filename}» προστατεύεται με κωδικό. Ανεβάστε ένα PDF χωρίς κωδικό.",
    "message.pdf_unreadable": "Δεν ήταν δυνατή η ανάγνωση του «{filename}». Είναι έγκυρο PDF;",
    "message.pdf_scanned":
      "Το «{filename}» μοιάζει με σαρωμένες εικόνες· προς το παρόν υποστηρίζονται μόνο PDF με κείμενο.",
    "message.file_unreadable": "Δεν ήταν δυνατή η ανάγνωση του «{filename}».",
    "message.audio_unreadable": "Δεν ήταν δυνατή η ανάγνωση του «{filename}» ως ήχου ή βίντεο (έχει ήχο;).",
    "message.no_speech": "Δεν βρέθηκε ομιλία στο «{filename}».",
    "message.material_too_long":
      "Το υλικό είναι πολύ μεγάλο ({length} χαρακτήρες· το όριο είναι {max}). Δοκιμάστε να το χωρίσετε σε περισσότερα σετ μελέτης.",
    "message.not_enough_material": "Δεν υπάρχει αρκετό υλικό για να δημιουργηθεί σετ μελέτης.",
    "message.study_set_not_found": "Το σετ μελέτης δεν βρέθηκε.",
    "message.chapter_not_found": "Το κεφάλαιο δεν βρέθηκε.",
    "message.question_not_found": "Η ερώτηση δεν βρέθηκε.",
    "message.quiz_locked": "Κερδίστε {count} ακόμη πόντους στο Κεφάλαιο {chapter} για να ξεκλειδώσετε αυτό το κουίζ.",
    "message.quiz_locked_one": "Κερδίστε 1 ακόμη πόντο στο Κεφάλαιο {chapter} για να ξεκλειδώσετε αυτό το κουίζ.",
    "message.already_answered": "Αυτή η ερώτηση έχει ήδη απαντηθεί.",
    "message.unsupported_type": "Ο τύπος του «{filename}» δεν υποστηρίζεται. Επιτρέπονται: {allowed}.",
    "message.file_empty": "Το «{filename}» είναι κενό.",
    "message.file_too_large": "Το «{filename}» είναι μεγαλύτερο από {max_mb} MB.",
    "message.nothing_uploaded": "Επιλέξτε τουλάχιστον ένα αρχείο ή επικολλήστε κείμενο.",
    "message.too_many_files": "Μπορείτε να ανεβάσετε έως {max} αρχεία.",
    "message.text_too_long": "Το κείμενο που επικολλήσατε είναι πολύ μεγάλο (έως {max} χαρακτήρες).",
    "message.title_too_long": "Ο τίτλος είναι πολύ μεγάλος (έως {max} χαρακτήρες).",
    "message.daily_limit_reached": "Μπορείτε να δημιουργήσετε έως {max} σετ μελέτης σε 24 ώρες.",
    "message.only_failed_retry": "Μόνο ένα σετ μελέτης που απέτυχε μπορεί να δοκιμαστεί ξανά.",
    "message.sign_in_required": "Συνδεθείτε.",
    "message.session_expired": "Η σύνδεσή σας έληξε. Συνδεθείτε ξανά.",
    "message.sign_in_unreachable": "Η υπηρεσία σύνδεσης δεν είναι διαθέσιμη. Δοκιμάστε ξανά.",
    "message.unknown": "Κάτι πήγε στραβά. Δοκιμάστε ξανά.",
  },
};
