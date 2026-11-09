export function dDayLabel(dDay: number | null): string {
	if (dDay === null) return "마감일 미정";
	if (dDay < 0) return "마감";
	if (dDay === 0) return "D-day";
	return `D-${dDay}`;
}

export function dDayTone(dDay: number | null): string {
	if (dDay === null) return "bg-slate-100 text-slate-600";
	if (dDay < 0) return "bg-slate-200 text-slate-500";
	if (dDay <= 7) return "bg-red-50 text-red-700";
	return "bg-emerald-50 text-emerald-700";
}

export const REFUSE_MESSAGES: Record<string, string> = {
	NO_MATCH: "조건에 맞는 공고가 없습니다.",
	LOW_RELEVANCE: "질문과 관련된 공고를 찾지 못했습니다.",
	NO_CITATION: "근거를 확인할 수 없어 답변하지 않았습니다.",
};

export const FILTER_LABELS: Record<string, string> = {
	region: "지역",
	target: "대상",
	bizAge: "업력",
	age: "연령",
	category: "분야",
	includeClosed: "마감 공고 포함",
	endFrom: "마감 시작",
	endTo: "마감 종료",
};

export const STAGE_LABELS: Record<string, string> = {
	analyze: "조건 분석",
	search: "검색",
	rerank: "재정렬",
	generate: "답변 생성",
};
