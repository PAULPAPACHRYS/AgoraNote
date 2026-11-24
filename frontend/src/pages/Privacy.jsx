/*
 Privacy.jsx: the privacy page (/privacy)
 it says what AgoraNote stores, where, and how to delete it
 anyone can open it, signed in or not (see App.jsx), so people can read it before creating an account

 the page is long prose with links in it, so it is written out once per language here instead of being cut into i18n.js texts
 keep both versions saying the same, and keep them true: when the setup changes (database host, AI provider), change this page with it
*/
import { Link } from "react-router-dom";
import { language } from "../i18n.js";

export default function Privacy() {
  return (
    <article className="prose privacy">
      {language === "el" ? <PrivacyGreek /> : <PrivacyEnglish />}
      <p className="muted small">
        {language === "el" ? "Τελευταία ενημέρωση: 20 Νοεμβρίου 2026" : "Last updated: 20 November 2026"}
      </p>
      <p>
        <Link to="/">{language === "el" ? "Πίσω στο AgoraNote" : "Back to AgoraNote"}</Link>
      </p>
    </article>
  );
}

function PrivacyEnglish() {
  return (
    <>
      <h1>Privacy</h1>
      <p>
        This page explains what AgoraNote stores about you, where it is kept and how to delete it.
        AgoraNote shows no ads, doesn't sell or share your data, and uses no analytics or tracking.
      </p>

      <h2>Your account: Clerk</h2>
      <p>
        Signing in is handled by <a href="https://clerk.com/legal/privacy">Clerk</a>, a company based
        in the United States. Clerk stores your account: your email address, your name and picture if
        you add them, your password or the account you sign in with (such as Google), and a list of
        the devices you are signed in on. AgoraNote never sees your password.
      </p>
      <p>
        AgoraNote's own database keeps only the ID that Clerk gives your account and your email address,
        so it knows which study sets are yours.
      </p>

      <h2>Your study material: Cloudflare R2 and AgoraNote's database</h2>
      <p>
        The files you upload (documents and recordings) are stored in{" "}
        <a href="https://www.cloudflare.com/privacypolicy/">Cloudflare</a> R2, an online storage
        service, in a private storage space that only AgoraNote's servers can open. The written
        transcripts of your recordings are kept there too.
      </p>
      <p>AgoraNote's database stores:</p>
      <ul>
        <li>the text taken from your files or pasted in, and the names and sizes of your files;</li>
        <li>
          everything made from it: chapters, summaries, key concepts, flashcards, study aids and quiz
          questions;
        </li>
        <li>your quiz answers, points and progress;</li>
        <li>your display settings (theme, text size and so on) and your language;</li>
        <li>
          when you created each study set in the last 24 hours, for the daily limit on new study sets.
          This is kept for 24 hours even if you delete the set.
        </li>
      </ul>
      <p>
        Other AgoraNote users can't see any of it. As with any website, the people who run AgoraNote can
        technically open the stored data. The servers also keep technical logs (for example, which
        address asked for which page, and when) to find and fix problems.
      </p>

      {/* update this section (in both languages) when the deployed app switches to a hosted AI provider*/}
      <h2>How your material is processed: AI</h2>
      <p>
        AgoraNote uses AI models to split your material into chapters, write the study material and
        quiz questions, and turn recordings into text. These models run on AgoraNote's own computer, so
        your material is not sent to any AI company and is not used to train AI models.
      </p>

      <h2>In your browser</h2>
      <ul>
        <li>
          Your display settings and language are saved in your browser, so they apply straight away,
          even before you sign in.
        </li>
        <li>
          Clerk keeps you signed in with cookies. They are needed for signing in and are not used for
          tracking.
        </li>
      </ul>

      <h2>How long it is kept, and how to delete it</h2>
      <p>Your material is kept until you delete it.</p>
      <ul>
        <li>
          <strong>One study set:</strong> open it and choose "Delete study set". Its files, transcripts
          and everything made from it are deleted straight away.
        </li>
        <li>
          <strong>Your whole account:</strong> open the account menu at the top right, choose "Manage
          account", then delete your account under "Security". Clerk deletes your account, and AgoraNote
          deletes all your study sets, files and progress.
        </li>
      </ul>
    </>
  );
}

//same as PrivacyEnglish but in Greek. the button names are the ones the Greek interface shows (Clerk's own menu included)
function PrivacyGreek() {
  return (
    <>
      <h1>Απόρρητο</h1>
      <p>
        Αυτή η σελίδα εξηγεί τι αποθηκεύει το AgoraNote για εσάς, πού φυλάσσεται και πώς μπορείτε να το
        διαγράψετε. Το AgoraNote δεν δείχνει διαφημίσεις, δεν πουλά και δεν μοιράζεται τα δεδομένα σας,
        και δεν χρησιμοποιεί εργαλεία ανάλυσης ή παρακολούθησης.
      </p>

      <h2>Ο λογαριασμός σας: Clerk</h2>
      <p>
        Τη σύνδεση τη διαχειρίζεται η <a href="https://clerk.com/legal/privacy">Clerk</a>, μια εταιρεία με
        έδρα στις Ηνωμένες Πολιτείες. Η Clerk αποθηκεύει τον λογαριασμό σας: τη διεύθυνση email σας, το
        όνομα και τη φωτογραφία σας αν τα προσθέσετε, τον κωδικό σας ή τον λογαριασμό με τον οποίο
        συνδέεστε (π.χ. Google), και μια λίστα με τις συσκευές στις οποίες είστε συνδεδεμένοι. Το AgoraNote
        δεν βλέπει ποτέ τον κωδικό σας.
      </p>
      <p>
        Η βάση δεδομένων του AgoraNote κρατά μόνο το αναγνωριστικό που δίνει η Clerk στον λογαριασμό σας
        και τη διεύθυνση email σας, ώστε να ξέρει ποια σετ μελέτης είναι δικά σας.
      </p>

      <h2>Το υλικό μελέτης σας: Cloudflare R2 και η βάση δεδομένων του AgoraNote</h2>
      <p>
        Τα αρχεία που ανεβάζετε (έγγραφα και ηχογραφήσεις) αποθηκεύονται στο R2 της{" "}
        <a href="https://www.cloudflare.com/privacypolicy/">Cloudflare</a>, μια υπηρεσία αποθήκευσης στο
        διαδίκτυο, σε έναν ιδιωτικό χώρο που μόνο οι διακομιστές του AgoraNote μπορούν να ανοίξουν. Εκεί
        φυλάσσονται και οι γραπτές απομαγνητοφωνήσεις των ηχογραφήσεών σας.
      </p>
      <p>Η βάση δεδομένων του AgoraNote αποθηκεύει:</p>
      <ul>
        <li>
          το κείμενο που προέρχεται από τα αρχεία σας ή που επικολλήσατε, και τα ονόματα και τα μεγέθη
          των αρχείων σας·
        </li>
        <li>
          ό,τι δημιουργείται από αυτό: κεφάλαια, περιλήψεις, βασικές έννοιες, κάρτες ερωτήσεων, βοηθήματα
          μελέτης και ερωτήσεις κουίζ·
        </li>
        <li>τις απαντήσεις σας στα κουίζ, τους πόντους και την πρόοδό σας·</li>
        <li>τις ρυθμίσεις εμφάνισης (θέμα, μέγεθος κειμένου κ.λπ.) και τη γλώσσα σας·</li>
        <li>
          πότε δημιουργήσατε κάθε σετ μελέτης τις τελευταίες 24 ώρες, για το ημερήσιο όριο νέων σετ
          μελέτης. Αυτό φυλάσσεται για 24 ώρες ακόμη κι αν διαγράψετε το σετ.
        </li>
      </ul>
      <p>
        Οι άλλοι χρήστες του AgoraNote δεν μπορούν να δουν τίποτα από αυτά. Όπως σε κάθε ιστότοπο, όσοι
        λειτουργούν το AgoraNote έχουν τεχνικά πρόσβαση στα αποθηκευμένα δεδομένα. Οι διακομιστές κρατούν
        επίσης τεχνικά αρχεία καταγραφής (για παράδειγμα, ποια διεύθυνση ζήτησε ποια σελίδα και πότε) για
        τον εντοπισμό και τη διόρθωση προβλημάτων.
      </p>

      <h2>Πώς επεξεργάζεται το υλικό σας: AI</h2>
      <p>
        Το AgoraNote χρησιμοποιεί μοντέλα AI για να χωρίσει το υλικό σας σε κεφάλαια, να γράψει το υλικό
        μελέτης και τις ερωτήσεις των κουίζ, και να μετατρέψει τις ηχογραφήσεις σε κείμενο. Αυτά τα μοντέλα
        τρέχουν στον υπολογιστή του ίδιου του AgoraNote, οπότε το υλικό σας δεν στέλνεται σε καμία εταιρεία
        AI και δεν χρησιμοποιείται για την εκπαίδευση μοντέλων AI.
      </p>

      <h2>Στο πρόγραμμα περιήγησής σας</h2>
      <ul>
        <li>
          Οι ρυθμίσεις εμφάνισης και η γλώσσα σας αποθηκεύονται στο πρόγραμμα περιήγησής σας, ώστε να
          ισχύουν αμέσως, ακόμη και πριν συνδεθείτε.
        </li>
        <li>
          Η Clerk σάς κρατά συνδεδεμένους με cookies. Χρειάζονται για τη σύνδεση και δεν χρησιμοποιούνται
          για παρακολούθηση.
        </li>
      </ul>

      <h2>Πόσο καιρό φυλάσσεται και πώς διαγράφεται</h2>
      <p>Το υλικό σας φυλάσσεται μέχρι να το διαγράψετε.</p>
      <ul>
        <li>
          <strong>Ένα σετ μελέτης:</strong> ανοίξτε το και επιλέξτε «Διαγραφή σετ μελέτης». Τα αρχεία του,
          οι απομαγνητοφωνήσεις και ό,τι δημιουργήθηκε από αυτό διαγράφονται αμέσως.
        </li>
        <li>
          <strong>Ολόκληρος ο λογαριασμός σας:</strong> ανοίξτε το μενού λογαριασμού πάνω δεξιά, επιλέξτε
          «Διαχείριση λογαριασμού» και διαγράψτε τον λογαριασμό σας στην ενότητα «Ασφάλεια». Η Clerk
          διαγράφει τον λογαριασμό σας και το AgoraNote διαγράφει όλα τα σετ μελέτης, τα αρχεία και την
          πρόοδό σας.
        </li>
      </ul>
    </>
  );
}
