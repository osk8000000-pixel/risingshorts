// 돈챙김 예적금 금리: 방문할 때 금융감독원 금융상품통합비교공시 오픈API에서 바로 받아 온다.
// 금감원 약관(정보 복제·저장 금지)에 따라 파일이나 데이터베이스에 저장하지 않는다.
// 같은 실행 환경 안에서만 몇 분간 재사용해 일일 조회 한도(10,000건)를 넘지 않게 한다.
const GROUPS = { bank: "020000", savings: "030300" };
const KEEP_MS = 10 * 60 * 1000;
const memo = {};

async function fetchKind(env, kind) {
  const ep = kind === "saving" ? "savingProductsSearch" : "depositProductsSearch";
  const out = [];
  let month = "";
  for (const [g, code] of Object.entries(GROUPS)) {
    let page = 1, max = 1;
    do {
      const r = await fetch(`https://finlife.fss.or.kr/finlifeapi/${ep}.json?auth=${env.FINLIFE_API_KEY}&topFinGrpNo=${code}&pageNo=${page}`);
      const j = (await r.json()).result;
      if (!j || j.err_cd !== "000") throw new Error((j && j.err_msg) || "금감원 응답 오류");
      max = Number(j.max_page_no) || 1;
      const opts = {};
      for (const o of j.optionList || []) (opts[o.fin_co_no + "|" + o.fin_prdt_cd] ||= []).push(o);
      for (const b of j.baseList || []) {
        month = month || b.dcls_month;
        const os = (opts[b.fin_co_no + "|" + b.fin_prdt_cd] || []).map((o) => ({
          t: Number(o.save_trm), r: o.intr_rate, r2: o.intr_rate2,
          type: o.intr_rate_type_nm || "", rsrv: o.rsrv_type_nm || "",
        }));
        out.push({
          g, bank: b.kor_co_nm, name: b.fin_prdt_nm, join: b.join_way || "",
          cond: b.spcl_cnd || "", member: b.join_member || "", limit: b.max_limit, note: b.etc_note || "",
          deny: b.join_deny, opts: os,
        });
      }
      page++;
    } while (page <= max && page <= 10);
  }
  return { kind, month, fetched: new Date().toISOString(), items: out };
}

export async function onRequestGet({ request, env }) {
  const kind = new URL(request.url).searchParams.get("kind") === "saving" ? "saving" : "deposit";
  const now = Date.now();
  try {
    if (!memo[kind] || now - memo[kind].t > KEEP_MS) memo[kind] = { t: now, d: await fetchKind(env, kind) };
    return new Response(JSON.stringify(memo[kind].d), {
      headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: "금리 정보를 잠시 불러오지 못했어요." }), {
      status: 502, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
    });
  }
}
