import { supabase } from "./supabase";

export type SavedNotice = {
	id: string;
	title: string;
	endDate: string | null;
	url: string;
};

export type HistoryItem = {
	question: string;
	refused: boolean;
	sourceCount: number;
	createdAt: string;
};

const BOOKMARKS_KEY = "grf.bookmarks";
const HISTORY_KEY = "grf.history";
const HISTORY_LIMIT = 50;

function readLocal<T>(key: string): T[] {
	try {
		const raw = localStorage.getItem(key);
		return raw ? (JSON.parse(raw) as T[]) : [];
	} catch {
		return [];
	}
}

function writeLocal<T>(key: string, items: T[]) {
	try {
		localStorage.setItem(key, JSON.stringify(items));
	} catch {
		// 브라우저 저장소를 쓸 수 없는 환경에서는 저장하지 않는다.
	}
}

// 같은 질문이 같은 시각에 두 번 들어 있으면 하나로 본다(밀리초 단위).
function historyKey(question: string, createdAt: string): string {
	return `${question}|${new Date(createdAt).toISOString()}`;
}

function dedupe(items: HistoryItem[]): HistoryItem[] {
	const seen = new Set<string>();
	return items.filter((h) => {
		const key = historyKey(h.question, h.createdAt);
		if (seen.has(key)) return false;
		seen.add(key);
		return true;
	});
}

// userId가 없으면 이 브라우저에, 있으면 계정(Supabase)에 저장한다.
export async function listBookmarks(
	userId: string | null,
): Promise<SavedNotice[]> {
	if (!userId || !supabase) return readLocal<SavedNotice>(BOOKMARKS_KEY);
	const { data, error } = await supabase
		.from("bookmarks")
		.select("notice_id,title,end_date,url")
		.order("created_at", { ascending: false });
	if (error) throw new Error(error.message);
	return (data ?? []).map((r) => ({
		id: r.notice_id,
		title: r.title,
		endDate: r.end_date,
		url: r.url ?? "",
	}));
}

export async function toggleBookmark(
	userId: string | null,
	notice: SavedNotice,
	on: boolean,
): Promise<void> {
	if (!userId || !supabase) {
		const rest = readLocal<SavedNotice>(BOOKMARKS_KEY).filter(
			(b) => b.id !== notice.id,
		);
		writeLocal(BOOKMARKS_KEY, on ? [notice, ...rest] : rest);
		return;
	}
	if (on) {
		const { error } = await supabase.from("bookmarks").upsert(
			{
				notice_id: notice.id,
				title: notice.title,
				end_date: notice.endDate,
				url: notice.url,
			},
			{ onConflict: "user_id,notice_id" },
		);
		if (error) throw new Error(error.message);
	} else {
		const { error } = await supabase
			.from("bookmarks")
			.delete()
			.eq("notice_id", notice.id);
		if (error) throw new Error(error.message);
	}
}

export async function listHistory(
	userId: string | null,
): Promise<HistoryItem[]> {
	if (!userId || !supabase) return dedupe(readLocal<HistoryItem>(HISTORY_KEY));
	const { data, error } = await supabase
		.from("history")
		.select("question,refused,source_count,created_at")
		.order("created_at", { ascending: false })
		.limit(HISTORY_LIMIT);
	if (error) throw new Error(error.message);
	return dedupe(
		(data ?? []).map((r) => ({
			question: r.question,
			refused: r.refused,
			sourceCount: r.source_count,
			createdAt: r.created_at,
		})),
	);
}

export async function addHistory(
	userId: string | null,
	item: HistoryItem,
): Promise<void> {
	if (!userId || !supabase) {
		const items = [item, ...readLocal<HistoryItem>(HISTORY_KEY)].slice(
			0,
			HISTORY_LIMIT,
		);
		writeLocal(HISTORY_KEY, items);
		return;
	}
	const { error } = await supabase.from("history").insert({
		question: item.question,
		refused: item.refused,
		source_count: item.sourceCount,
	});
	if (error) throw new Error(error.message);
}

// 로그인하면 이 브라우저에 저장했던 항목을 계정으로 옮기고, 성공하면 브라우저 쪽은 비운다.
// 계정에 이미 같은 이력(질문과 시각이 같음)이 있으면 다시 넣지 않는다.
async function migrateOnce(): Promise<void> {
	if (!supabase) return;
	const bookmarks = readLocal<SavedNotice>(BOOKMARKS_KEY);
	const history = dedupe(readLocal<HistoryItem>(HISTORY_KEY));
	if (bookmarks.length > 0) {
		const { error } = await supabase.from("bookmarks").upsert(
			bookmarks.map((b) => ({
				notice_id: b.id,
				title: b.title,
				end_date: b.endDate,
				url: b.url,
			})),
			{ onConflict: "user_id,notice_id" },
		);
		if (error) throw new Error(error.message);
	}
	if (history.length > 0) {
		const { data: remote, error: readError } = await supabase
			.from("history")
			.select("question,created_at");
		if (readError) throw new Error(readError.message);
		const existing = new Set(
			(remote ?? []).map((r) => historyKey(r.question, r.created_at)),
		);
		const fresh = history.filter(
			(h) => !existing.has(historyKey(h.question, h.createdAt)),
		);
		if (fresh.length > 0) {
			const { error } = await supabase.from("history").insert(
				fresh.map((h) => ({
					question: h.question,
					refused: h.refused,
					source_count: h.sourceCount,
					created_at: h.createdAt,
				})),
			);
			if (error) throw new Error(error.message);
		}
	}
	writeLocal(BOOKMARKS_KEY, []);
	writeLocal(HISTORY_KEY, []);
}

export async function migrateLocalToAccount(): Promise<void> {
	// 탭이 둘 이상 열려 있어도 한 번에 하나씩만 옮긴다.
	if (typeof navigator !== "undefined" && navigator.locks) {
		await navigator.locks.request("grf-migrate", migrateOnce);
		return;
	}
	await migrateOnce();
}
