import { createClient, type SupabaseClient } from "@supabase/supabase-js";

function create(): SupabaseClient | null {
	const rawUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
	const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as
		| string
		| undefined;
	if (!rawUrl || !key) return null;
	try {
		// 끝의 "/"나 경로가 붙어 있어도 https://<프로젝트>.supabase.co 형태만 쓴다.
		const origin = new URL(rawUrl.trim()).origin;
		return createClient(origin, key.trim());
	} catch {
		// 값이 잘못되어도 로그인 기능만 끄고 앱은 그대로 동작한다.
		return null;
	}
}

export const supabase = create();
