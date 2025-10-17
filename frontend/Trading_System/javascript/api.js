const API =
  (typeof import !== "undefined" && import.meta && import.meta.env && import.meta.env.VITE_API_URL)
  || (typeof window !== "undefined" && window.API_BASE_URL)
  || "http://ec2-54-205-226-205.compute-1.amazonaws.com";

const BASE_URL = API; // change if needed

function token(){ return localStorage.getItem("token") || ""; }
function setToken(t){ localStorage.setItem("token", t); }
function clearToken(){ localStorage.removeItem("token"); }
export function logout(){ clearToken(); location.href = "./login.html"; }

async function http(path, { method="GET", body, auth=false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) headers["Authorization"] = `Bearer ${token()}`;
  const res = await fetch(`${BASE_URL}${path}`, {
    method, headers, body: body ? JSON.stringify(body) : undefined
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || res.statusText);
  return data;
}

// Auth
export async function registerUser({ full_name, username, email, password }) {
  const r = await http("/auth/register", { method:"POST", body:{ full_name, username, email, password }});
  setToken(r.access_token); return r;
}
export async function loginUser({ username, password }) {
  const r = await http("/auth/login", { method:"POST", body:{ username, password }});
  setToken(r.access_token); return r;
}

// Market
export async function listTickers(){ return http("/market/tickers"); }

// Account & Cash
export async function getBalance(){ return http("/account", { auth:true }); }
export async function deposit(amount){ return http("/cash/deposit", { method:"POST", auth:true, body:{ amount: Number(amount) }}); }
export async function withdraw(amount){ return http("/cash/withdraw", { method:"POST", auth:true, body:{ amount: Number(amount) }}); }

// Trades & Portfolio
export async function placeOrder({ ticker, side, quantity }){
  return http("/trades/order", { method:"POST", auth:true, body:{ ticker, side, quantity: Number(quantity) }});
}
export async function getHoldings(){ return http("/portfolio/holdings", { auth:true }); }
export async function getTransactions(){ return http("/portfolio/transactions", { auth:true }); }

// Guards/helpers
export function requireAuth(){
  if (!token()) location.href = "./login.html";
}
export async function renderCash(spanId="cash-amount"){
  try {
    const { cash_balance } = await getBalance();
    const el = document.getElementById(spanId);
    if (el) el.textContent = Number(cash_balance).toLocaleString(undefined,{minimumFractionDigits:2, maximumFractionDigits:2});
  } catch {}
}

//Administrator Stock Creator
// In/assets/api.js - add this export note: If your backend route differs, change "/admin/stocks" accordingly
export async function adminCreateStock(payload) {
		//expects: { ticker, company_name, current_price, volume?, sector?, is_listed? }
		return http("/admin/stocks", {method: "POST", auth: true, body: payload });
}