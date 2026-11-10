import type { HistoryItem, SavedNotice } from "../saved";

type Props = {
	bookmarks: SavedNotice[];
	history: HistoryItem[];
	loggedIn: boolean;
	onRemove: (notice: SavedNotice) => void;
	error?: string | null;
};

export function SavedView({
	bookmarks,
	history,
	loggedIn,
	onRemove,
	error,
}: Props) {
	return (
		<div className="space-y-6">
			{error && (
				<p
					role="alert"
					className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700"
				>
					{error}
				</p>
			)}
			<p className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-600">
				{loggedIn
					? "계정에 저장된 항목입니다. 다른 기기에서 로그인해도 볼 수 있습니다."
					: "이 브라우저에만 저장된 항목입니다. 로그인하면 계정으로 옮겨져 다른 기기에서도 볼 수 있습니다."}
			</p>

			<section className="space-y-2">
				<h2 className="text-sm font-semibold text-slate-700">
					관심 공고 {bookmarks.length}건
				</h2>
				{bookmarks.length === 0 && (
					<p className="text-sm text-slate-500">
						질문 탭의 근거 공고 카드에서 "저장"을 누르면 여기에 모입니다.
					</p>
				)}
				{bookmarks.map((b) => (
					<article
						key={b.id}
						className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3"
					>
						<div>
							<h3 className="text-sm font-medium text-slate-900">{b.title}</h3>
							<p className="mt-0.5 text-xs text-slate-500">
								[{b.id}]{b.endDate ? ` · 마감 ${b.endDate}` : ""}
							</p>
							{b.url && (
								<a
									href={b.url}
									target="_blank"
									rel="noreferrer"
									className="mt-1 inline-block text-xs font-medium text-blue-700 hover:underline"
								>
									원문 공고 보기 ↗
								</a>
							)}
						</div>
						<button
							type="button"
							onClick={() => onRemove(b)}
							className="shrink-0 rounded border border-slate-300 px-2 py-0.5 text-xs hover:bg-slate-100"
						>
							삭제
						</button>
					</article>
				))}
			</section>

			<section className="space-y-2">
				<h2 className="text-sm font-semibold text-slate-700">
					질문 이력 {history.length}건
				</h2>
				{history.length === 0 && (
					<p className="text-sm text-slate-500">아직 질문 이력이 없습니다.</p>
				)}
				{history.map((h) => (
					<div
						key={`${h.createdAt}-${h.question}`}
						className="rounded-lg border border-slate-200 bg-white p-3 text-sm"
					>
						<p className="text-slate-900">{h.question}</p>
						<p className="mt-0.5 text-xs text-slate-500">
							{h.refused ? "답변하지 않음" : `출처 ${h.sourceCount}건`} ·{" "}
							{new Date(h.createdAt).toLocaleString("ko-KR")}
						</p>
					</div>
				))}
			</section>
		</div>
	);
}
