import { dDayLabel, dDayTone } from "../format";
import type { Source } from "../types";

export function SourceCard({ source }: { source: Source }) {
	const meta = [source.region, source.category, source.agency]
		.filter(Boolean)
		.join(" · ");
	return (
		<article
			id={`src-${source.id}`}
			className="scroll-mt-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
		>
			<div className="flex items-start justify-between gap-3">
				<h3 className="text-sm font-semibold text-slate-900">{source.title}</h3>
				<span
					className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${dDayTone(source.dDay)}`}
				>
					{dDayLabel(source.dDay)}
				</span>
			</div>
			<p className="mt-1 text-xs text-slate-500">
				[{source.id}] {meta}
				{source.endDate ? ` · 마감 ${source.endDate}` : ""}
			</p>
			{source.snippet && (
				<p className="mt-2 text-sm text-slate-700">{source.snippet}</p>
			)}
			{source.flags.length > 0 && (
				<div className="mt-2 flex flex-wrap gap-1">
					{source.flags.map((flag) => (
						<span
							key={flag}
							className="rounded bg-amber-50 px-1.5 py-0.5 text-xs text-amber-800"
						>
							{flag}
						</span>
					))}
				</div>
			)}
			<a
				href={source.url}
				target="_blank"
				rel="noreferrer"
				className="mt-3 inline-block text-xs font-medium text-blue-700 hover:underline"
			>
				원문 공고 보기 ↗
			</a>
		</article>
	);
}
