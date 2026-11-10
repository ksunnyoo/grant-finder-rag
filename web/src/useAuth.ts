import type { Session } from "@supabase/supabase-js";
import { useEffect, useState } from "react";
import { supabase } from "./supabase";

export function useAuth(): Session | null {
	const [session, setSession] = useState<Session | null>(null);
	useEffect(() => {
		if (!supabase) return;
		void supabase.auth
			.getSession()
			.then(({ data }) => setSession(data.session));
		const { data } = supabase.auth.onAuthStateChange((_event, next) =>
			setSession(next),
		);
		return () => data.subscription.unsubscribe();
	}, []);
	return session;
}
