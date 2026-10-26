const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** '2026-10-30' -> '30 Oct 2026'. Anything that is not a date is returned as it is. */
export function prettyDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
  return m ? `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}` : iso || '';
}

/** Today in Singapore (UTC+8), the team's timezone, as YYYY-MM-DD. */
export function todaySgt(): string {
  return new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);
}
