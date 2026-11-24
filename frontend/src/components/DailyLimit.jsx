/*
 DailyLimit.jsx: the daily limit on new study sets, shown on the dashboard and the New study set page:
 how many new sets are left, or (when the limit is reached) from when the next one is possible

 `usage` is GET /api/study-sets/usage: {limit, used, next_free_at}
 limit 0 = no limit (nothing is shown), next_free_at is only set when the limit is reached
 null = not loaded: nothing is shown either
*/
import { formatDateTime, t } from "../i18n.js";

export default function DailyLimit({ usage }) {
  if (!usage || usage.limit === 0) return null;
  if (usage.next_free_at) {
    return (
      <div className="limit-reached">
        <p className="locked-title">{t("new.limit_reached_title")}</p>
        <p>{t("new.limit_reached", { max: usage.limit, time: formatDateTime(usage.next_free_at) })}</p>
      </div>
    );
  }
  return <p className="muted small">{t("new.limit_left", { count: usage.limit - usage.used, max: usage.limit })}</p>;
}
