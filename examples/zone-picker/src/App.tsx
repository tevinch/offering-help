import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { DatePicker } from 'antd';
import luxonGenerateConfig from '@rc-component/picker/generate/luxon';
import { DateTime, Settings } from 'luxon';
import { parseWall, validZone, WALL_FORMAT, type RepeatPolicy } from './time';

const Picker = DatePicker.generatePicker<DateTime>(luxonGenerateConfig);
const FORMAT = 'YYYY-MM-DD HH:mm:ss';
const STORAGE_KEY = 'report-times-v1';
type Field = 'dateTime' | 'time' | 'start' | 'end';
interface Saved {
  zone: string;
  policy: RepeatPolicy;
  dateTime: string | null;
  time: string | null;
  range: [string, string] | null;
  anchor: string;
}
interface Report { id: string; name: string; at: string }
const EMPTY: Saved = { zone: 'UTC', policy: 'earlier', dateTime: null, time: null, range: null, anchor: '2026-05-25' };
const SAMPLE = { dateTime: '2026-05-25T18:00:00.000Z', time: '2026-05-25T18:00:00.000Z', range: ['2026-05-25T17:00:00.000Z', '2026-05-25T19:00:00.000Z'] as [string, string] };
const utcValue = (value: unknown): value is string => typeof value === 'string' && value.endsWith('Z') && DateTime.fromISO(value).isValid;

function initialState(): Saved {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null') as Saved | null;
    if (value && validZone(value.zone) && ['earlier', 'later'].includes(value.policy)
      && (value.dateTime === null || utcValue(value.dateTime))
      && (value.time === null || utcValue(value.time))
      && (value.range === null || (Array.isArray(value.range) && value.range.length === 2 && value.range.every(utcValue)))
      && typeof value.anchor === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value.anchor) && DateTime.fromISO(value.anchor).isValid) return value;
  } catch { /* An unavailable or invalid saved preference starts with empty controls. */ }
  return EMPTY;
}

export default function App() {
  const [saved, setSaved] = useState(initialState);
  // This application owns one browser session. Never set this per request in SSR.
  Settings.defaultZone = saved.zone;
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});
  const drafts = useRef<Partial<Record<Field, string>>>({});
  const [draftCount, setDraftCount] = useState(0);
  const [revision, setRevision] = useState({ dateTime: 0, time: 0, range: 0 });
  const [status, setStatus] = useState('Choose a report time, then query the sample data.');
  const [payload, setPayload] = useState<object | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [busy, setBusy] = useState(false);
  const [storageNotice, setStorageNotice] = useState('');
  const asValue = (value: string | null) => {
    const date = value ? DateTime.fromISO(value, { zone: saved.zone }) : null;
    return date?.isValid ? date : null;
  };
  // Keep controlled values stable while the picker is editing an uncommitted draft.
  const displayed = useMemo(() => ({
    dateTime: asValue(saved.dateTime),
    time: asValue(saved.time),
    range: saved.range ? [asValue(saved.range[0]), asValue(saved.range[1])] as [DateTime<true> | null, DateTime<true> | null] : null,
  }), [saved.dateTime, saved.time, saved.range, saved.zone]);
  const timeValue = displayed.time;
  const anchor = timeValue?.toISODate() ?? saved.anchor;
  const dateTimeOptions = useMemo(() => ({ defaultOpenValue: DateTime.now().startOf('day') }), [saved.zone]);
  const rangeTimeOptions = useMemo(() => ({ defaultOpenValue: [DateTime.now().startOf('day'), DateTime.now().startOf('day')] }), [saved.zone]);
  const anchoredDefault = useMemo(() => DateTime.fromISO(anchor, { zone: saved.zone }), [anchor, saved.zone]);
  const zones = [...new Set(['UTC', 'America/Cuiaba', 'America/New_York', 'Asia/Kathmandu', ...Intl.supportedValuesOf('timeZone')])].sort();
  const blocked = draftCount > 0 || Object.values(errors).some(Boolean);

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(saved)); }
    catch { setStorageNotice('Browser storage is unavailable. Your current entries still work, but will not survive a reload.'); }
  }, [saved]);

  function forget(fields: Field[]) {
    fields.forEach(field => delete drafts.current[field]);
    setDraftCount(Object.keys(drafts.current).length);
    setErrors(previous => {
      const next = { ...previous };
      fields.forEach(field => delete next[field]);
      return next;
    });
  }

  function wall(field: Field, text: string): DateTime {
    return parseWall(field === 'time' ? `${anchor} ${text}` : text, saved.zone, saved.policy);
  }

  function capture(event: FormEvent<HTMLDivElement>) {
    const input = event.target;
    if (!(input instanceof HTMLInputElement)) return;
    const field = input.dataset.field as Field | undefined;
    const byId: Record<string, Field> = { 'report-date': 'dateTime', 'report-time': 'time', 'range-start': 'start', 'range-end': 'end' };
    const key = field ?? byId[input.id];
    if (!key) return;
    drafts.current[key] = input.value;
    setDraftCount(Object.keys(drafts.current).length);
    try {
      if (input.value) wall(key, input.value);
      setErrors(previous => ({ ...previous, [key]: undefined }));
    } catch (error) {
      setErrors(previous => ({ ...previous, [key]: (error as Error).message }));
    }
  }

  function commit(field: 'dateTime' | 'time', value: DateTime | null) {
    if (!value) {
      setSaved(previous => ({ ...previous, [field]: null, anchor: field === 'time' ? anchor : previous.anchor }));
      forget([field]); return;
    }
    try {
      // Raw text guards against a library-normalized DST gap. A later panel/Now
      // selection, however, is authoritative once that text is valid or cleared.
      if (drafts.current[field]) wall(field, drafts.current[field]);
      const text = value.toFormat(field === 'time' ? 'HH:mm:ss' : WALL_FORMAT);
      const instant = wall(field, text).toUTC().toISO()!;
      setSaved(previous => ({ ...previous, [field]: instant }));
      forget([field]);
    } catch (error) { setErrors(previous => ({ ...previous, [field]: (error as Error).message })); }
  }

  function commitRange(values: [DateTime | null, DateTime | null] | null) {
    if (!values) { setSaved(previous => ({ ...previous, range: null })); forget(['start', 'end']); return; }
    if (!values[0] || !values[1]) return;
    try {
      if (drafts.current.start) wall('start', drafts.current.start);
      if (drafts.current.end) wall('end', drafts.current.end);
      const start = wall('start', values[0].toFormat(WALL_FORMAT));
      const end = wall('end', values[1].toFormat(WALL_FORMAT));
      if (start > end) throw new Error('The range end must not precede its start.');
      setSaved(previous => ({ ...previous, range: [start.toUTC().toISO()!, end.toUTC().toISO()!] }));
      forget(['start', 'end']);
    } catch (error) { setErrors(previous => ({ ...previous, end: (error as Error).message })); }
  }

  function finishUnchanged() {
    const displayed: Record<Field, string> = {
      dateTime: asValue(saved.dateTime)?.toFormat(WALL_FORMAT) ?? '',
      time: timeValue?.toFormat('HH:mm:ss') ?? '',
      start: asValue(saved.range?.[0] ?? null)?.toFormat(WALL_FORMAT) ?? '',
      end: asValue(saved.range?.[1] ?? null)?.toFormat(WALL_FORMAT) ?? '',
    };
    forget((Object.keys(drafts.current) as Field[]).filter(field => drafts.current[field] === displayed[field]));
  }

  function clear(field: 'dateTime' | 'time' | 'range') {
    setSaved(previous => ({ ...previous, [field]: null, anchor: field === 'time' ? anchor : previous.anchor }));
    forget(field === 'range' ? ['start', 'end'] : [field]);
    setRevision(previous => ({ ...previous, [field]: previous[field] + 1 }));
  }

  async function query() {
    if (blocked || busy) return;
    const body = { zone: saved.zone, dateTime: saved.dateTime, time: saved.time, range: saved.range };
    setBusy(true);
    setStatus('Querying…');
    try {
      const response = await fetch('/api/reports', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!response.ok) throw new Error(`Request failed (${response.status}).`);
      const result = await response.json() as { reports: Report[] };
      setPayload(body);
      setReports(result.reports);
      setStatus(`Query complete: ${result.reports.length} matching reports.`);
    } catch (error) { setStatus((error as Error).message); }
    finally { setBusy(false); }
  }

  return <main>
    <header><p className="eyebrow">Ant Design + Luxon</p><h1>Report times</h1><p>Choose wall times in one shared time zone. Send exact UTC instants to your report query.</p></header>
    <section className="settings" aria-label="Time settings">
      <label>Display time zone<select value={saved.zone} disabled={draftCount > 0} onChange={event => setSaved(previous => ({ ...previous, zone: event.target.value }))}>{zones.map(zone => <option key={zone}>{zone}</option>)}</select></label>
      <label>Repeated wall times<select value={saved.policy} disabled={draftCount > 0} onChange={event => setSaved(previous => ({ ...previous, policy: event.target.value as RepeatPolicy }))}><option value="earlier">Use the earlier instant</option><option value="later">Use the later instant</option></select></label>
      <p className="hint">The repeated-time choice applies to new selections during a backward clock change. Existing instants stay unchanged. Typed times skipped by a forward clock change are rejected. A panel choice may move to the next valid time; check the displayed time before OK.</p>
    </section>
    <p className="hint">Type a value and press Enter or OK to commit it. Finish the current edit before changing zones. The time zone is <strong>{saved.zone}</strong>; your browser may use another zone.</p>
    <div onChange={capture} onBlurCapture={finishUnchanged}>
      <section className="field">
        <label htmlFor="report-date">Report date and time</label>
        <div className="row"><Picker key={revision.dateTime} id="report-date" value={displayed.dateTime} format={FORMAT} showTime={dateTimeOptions} preserveInvalidOnBlur onChange={value => commit('dateTime', value)} /><button onClick={() => clear('dateTime')}>Clear date</button></div>
      </section>
      <section className="field">
        <label htmlFor="report-time">Report time</label>
        <div className="row"><Picker key={revision.time} id="report-time" picker="time" mode={undefined} format="HH:mm:ss" value={timeValue} defaultOpenValue={anchoredDefault} preserveInvalidOnBlur onChange={value => commit('time', value)} /><button onClick={() => clear('time')}>Clear time</button>
          <label className="anchor">Time reference date<input type="date" value={anchor} disabled={draftCount > 0} onChange={event => {
            const nextAnchor = event.target.value;
            if (!nextAnchor) return;
            try {
              const nextTime = timeValue ? parseWall(`${nextAnchor} ${timeValue.toFormat('HH:mm:ss')}`, saved.zone, saved.policy).toUTC().toISO()! : null;
              setSaved(previous => ({ ...previous, anchor: nextAnchor, time: nextTime })); forget(['time']);
            } catch (error) { setErrors(previous => ({ ...previous, time: (error as Error).message })); }
          }} /></label>
        </div>
        <p className="hint">Time-only entry is attached to this date in the selected zone. A time without a date cannot identify an instant.</p>
      </section>
      <section className="field">
        <div className="range-labels"><label htmlFor="range-start">Range start</label><label htmlFor="range-end">Range end</label></div>
        <div className="row"><Picker.RangePicker key={revision.range} id={{ start: 'range-start', end: 'range-end' }} value={displayed.range} format={FORMAT} showTime={rangeTimeOptions} order={false} preserveInvalidOnBlur onChange={commitRange} /><button onClick={() => clear('range')}>Clear range</button></div>
      </section>
    </div>
    {Object.values(errors).some(Boolean) && <div role="alert">{[...new Set(Object.values(errors).filter(Boolean))].map(message => <p key={message}>{message}</p>)}<p>Correct the typed value or clear that control before choosing another time.</p></div>}
    {draftCount > 0 && !Object.values(errors).some(Boolean) && <p className="hint">Finish the current picker selection with Enter or OK before querying.</p>}
    <div className="actions"><button className="primary" onClick={query} disabled={blocked || busy}>Query reports</button><button onClick={() => {
      forget(['dateTime', 'time', 'start', 'end']); setSaved(previous => ({ ...previous, ...SAMPLE }));
      setRevision(previous => ({ dateTime: previous.dateTime + 1, time: previous.time + 1, range: previous.range + 1 }));
    }}>Load saved UTC example</button></div>
    <p role="status">{status}</p>
    {storageNotice && <p>{storageNotice}</p>}
    <section data-testid="results" aria-label="Query results"><h2>Matching reports</h2><p className="hint">The local sample endpoint matches exact date/time values and includes both range boundaries. Empty controls omit that filter.</p><ul>{reports.map(report => <li key={report.id}><strong>{report.name}</strong> — {DateTime.fromISO(report.at, { zone: saved.zone }).toFormat(WALL_FORMAT)} ({saved.zone})</li>)}</ul></section>
    {payload && <section><h2>Last submitted JSON</h2><pre>{JSON.stringify(payload, null, 2)}</pre></section>}
  </main>;
}
