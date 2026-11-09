import type { AskResponse, FilterInput, Meta } from "./types";

export class ApiError extends Error {
	code: string;

	constructor(code: string, message: string) {
		super(message);
		this.code = code;
	}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	let res: Response;
	try {
		res = await fetch(path, init);
	} catch {
		throw new ApiError(
			"NETWORK",
			"서버에 연결할 수 없습니다. 백엔드 서버가 켜져 있는지 확인해 주십시오.",
		);
	}
	if (!res.ok) {
		let code = "UNKNOWN";
		let message = `요청에 실패했습니다 (${res.status}).`;
		try {
			const body = await res.json();
			code = body.error?.code ?? code;
			message = body.error?.message ?? message;
		} catch {
			// 응답 본문이 JSON이 아니면 기본 메시지를 쓴다
		}
		throw new ApiError(code, message);
	}
	return res.json() as Promise<T>;
}

export const fetchMeta = () => request<Meta>("/api/meta");

export const askQuestion = (question: string, filters: FilterInput) =>
	request<AskResponse>("/api/ask", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ question, filters }),
	});
