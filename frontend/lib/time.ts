/** API timestamps from the database are UTC when no timezone is supplied. */
export function parseApiTimestamp(value: string): number {
  const hasTimezone = /[zZ]|[+-]\d{2}:\d{2}$/.test(value);
  return new Date(hasTimezone ? value : `${value}Z`).getTime();
}
