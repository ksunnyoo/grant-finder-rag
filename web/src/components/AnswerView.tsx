import { FILTER_LABELS, REFUSE_MESSAGES } from "../format";
import type { AskResponse } from "../types";

const CITATION = /(\[\d+(?:\s*,\s*\d+)*\])/;
const CITATION_ONLY = /^\[(\d+(?:\s*,\s*\d+)*)\]$/;

function splitAnswer(text: string) {
	let offset = 0;
	return text
		.replace(/^[*-] /gm, "• ")
		.split(CITATION)
		.map((part) => {
			const item = { key: String(offset), part };
			offset += part.length;
			return item;
		});
}

function AnswerText({ text }: { text: string }) {
	return (
		<p className="whitespace-pre-wrap text-sm leading-7 text-slate-800">
			{splitAnswer(text).map(({ key, part }) => {
				const m = part.match(CITATION_ONLY);
				if (!m) return part;
				return m[1].split(",").map((raw) => {
					const id = raw.trim();
					return (
						<a
							key={`${key}-${id}`}
							href={`#src-${id}`}
							className="mx-0.5 rounded bg-blue-50 px-1 text-xs font-medium text-blue-700 hover:bg-blue-100"
						>
							[{id}]
						</a>
					);
				});
			})}
		</p>
	);
}

function filterChips(filters: Record<string, unknown>): string[] {
	const chips: string[] = [];
	for (const [key, value] of Object.entries(filters)) {
		const label = FILTER_LABELS[key];
		if (!label) continue;
		if (
			value === false ||
			value === null ||
			(Array.isArray(value) && value.length === 0)
		)
			continue;
		chips.push(
			value === true
				? label
				: `${label}: ${Array.isArray(value) ? value.join(", ") : String(value)}`,
		);
	}
	return chips;
}

export function AnswerView({ result }: { result: AskResponse }) {
	const chips = filterChips(result.appliedFilters);
	return (
		<section className="space-y-3">
			{result.refused ? (
				<div className="rounded-lg border border-amber-300 bg-amber-50 p-4">
					<p className="text-sm font-semibold text-amber-900">
						답변하지 않았습니다
					</p>
					<p className="mt-1 text-sm text-amber-900">
						{REFUSE_MESSAGES[result.refuseReason ?? ""] ??
							"근거를 찾지 못했습니다."}
					</p>
					<p className="mt-2 text-xs text-amber-800">
						조건을 바꾸거나, 마감된 공고 포함을 켜거나, 질문을 더 구체적으로
						바꿔 보십시오.
					</p>
				</div>
			) : (
				<div className="rounded-lg border border-slate-200 bg-white p-4">
					<AnswerText text={result.answer} />
				</div>
			)}
			{chips.length > 0 && (
				<div className="flex flex-wrap items-center gap-1.5">
					<span className="text-xs text-slate-500">적용된 조건</span>
					{chips.map((chip) => (
						<span
							key={chip}
							className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700"
						>
							{chip}
						</span>
					))}
				</div>
			)}
		</section>
	);
}
