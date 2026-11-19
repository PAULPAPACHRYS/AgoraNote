// Privacy.jsx: the privacy page (/privacy). It says what AgoraNote stores, where, and how to delete it.
// Anyone can open it, signed in or not (see App.jsx), so people can read it before creating an account.
//
// Keep it true: when the setup changes (database host, AI provider), change this page with it.
import { Link } from "react-router-dom";

export default function Privacy() {
  return (
    <article className="prose privacy">
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
        <li>your display settings (theme, text size and so on).</li>
      </ul>
      <p>
        Other AgoraNote users can't see any of it. As with any website, the people who run AgoraNote can
        technically open the stored data. The servers also keep technical logs (for example, which
        address asked for which page, and when) to find and fix problems.
      </p>

      {/* Phase 10: update this section when the deployed app switches to a hosted AI provider. */}
      <h2>How your material is processed: AI</h2>
      <p>
        AgoraNote uses AI models to split your material into chapters, write the study material and
        quiz questions, and turn recordings into text. These models run on AgoraNote's own computer, so
        your material is not sent to any AI company and is not used to train AI models.
      </p>

      <h2>In your browser</h2>
      <ul>
        <li>
          Your display settings are saved in your browser, so they apply straight away, even before you
          sign in.
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

      <p className="muted small">Last updated: 19 November 2026</p>
      <p>
        <Link to="/">Back to AgoraNote</Link>
      </p>
    </article>
  );
}
