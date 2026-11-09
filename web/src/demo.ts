import type { AskResponse } from "./types";

export type DemoData = {
	asOfDate: string;
	generatedAt: string;
	items: { question: string; response: AskResponse }[];
};

export async function loadDemo(): Promise<DemoData> {
	const res = await fetch(`${import.meta.env.BASE_URL}demo/demo.json`);
	if (!res.ok) throw new Error("데모 데이터를 불러오지 못했습니다.");
	return res.json() as Promise<DemoData>;
}
