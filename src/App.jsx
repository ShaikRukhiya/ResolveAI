import { useEffect, useMemo, useState } from "react";
import {
  ArrowDownLeft, ArrowLeft, ArrowRight, ArrowUpRight, BadgeCheck, Bell, Bot,
  Check, CheckCircle2, ChevronDown, CircleHelp, Clock3, FileText, Headphones,
  Landmark, Menu, MessageCircle, MessageSquareText, MoreHorizontal, Plus,
  Search, Send, ShieldCheck, Sparkles, WalletCards, X,
} from "lucide-react";
import { BrowserRouter, Link, NavLink, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { api } from "./api";

const navItems = [
  { to: "/app/dashboard", label: "Overview", icon: Landmark },
  { to: "/app/transactions", label: "Transactions", icon: WalletCards },
  { to: "/app/assistant", label: "AI assistant", icon: Sparkles },
  { to: "/app/refunds", label: "Refunds", icon: ArrowDownLeft },
  { to: "/app/complaints", label: "Complaints", icon: MessageSquareText },
];

const money = (amount) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount);
const dateLabel = (value, options = { day: "numeric", month: "short", year: "numeric" }) =>
  value ? new Date(value).toLocaleDateString("en-IN", options) : "—";
const timeLabel = (value) => value ? new Date(value).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }) : "—";
const titleCase = (value = "") => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

function StatusBadge({ status }) {
  return <span className={`status-badge status-${status}`}>{titleCase(status)}</span>;
}

function ErrorNotice({ message, onRetry }) {
  return <div className="notice notice-error"><CircleHelp size={18} /><span>{message}</span>{onRetry && <button className="text-button" onClick={onRetry}>Try again</button>}</div>;
}

function LandingPage() {
  return (
    <main className="landing">
      <header className="landing-nav">
        <Link className="brand" to="/"><span className="brand-mark"><ShieldCheck size={20} /></span><span>Resolve<span className="brand-light">AI</span></span></Link>
        <div className="landing-links"><a href="#how-it-works">How it works</a><a href="#features">Features</a><Link className="button button-outline" to="/app/dashboard">Sign in</Link></div>
      </header>
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-dot" /> PAYMENT SUPPORT, MADE HUMAN</div>
          <h1>Clarity for every<br /><span>payment journey.</span></h1>
          <p>Understand what happened, know what to do next. ResolveAI brings your payment details and practical support together in one calm, clear place.</p>
          <div className="hero-actions"><Link className="button button-primary" to="/app/dashboard">Explore the demo <ArrowRight size={17} /></Link><a className="button button-quiet" href="#how-it-works">See how it works</a></div>
          <div className="hero-trust"><ShieldCheck size={16} /><span>Built for clarity. Your choices stay in your hands.</span></div>
        </div>
        <div className="hero-art" aria-label="ResolveAI sample payment overview">
          <div className="art-glow" />
          <div className="preview-card">
            <div className="preview-top"><div><span className="muted small">YOUR PAYMENT OVERVIEW</span><h3>Good morning, Rukhiya</h3></div><div className="preview-avatar">R</div></div>
            <div className="preview-balance"><span className="muted small">Payments this month</span><strong>₹8,372</strong><span className="balance-note"><ArrowUpRight size={14} /> 8 transactions</span></div>
            <div className="preview-row"><span className="preview-icon"><Landmark size={17} /></span><span><b>Blue Tokai Coffee</b><small>UPI · Today, 9:41 AM</small></span><strong>−₹485</strong><CheckCircle2 size={17} className="blue-icon" /></div>
            <div className="preview-row"><span className="preview-icon"><WalletCards size={17} /></span><span><b>Metro Recharge</b><small>UPI · Yesterday</small></span><strong>−₹300</strong><Clock3 size={17} className="amber-icon" /></div>
            <div className="ai-nudge"><span className="nudge-icon"><Sparkles size={16} /></span><div><b>Need a hand with a payment?</b><small>Get a clear answer, based on your transactions.</small></div><ArrowRight size={16} /></div>
          </div>
          <div className="floating-chip"><span className="floating-icon"><MessageCircle size={16} /></span><span><b>Here to help</b><small>In your language</small></span></div>
        </div>
      </section>
      <section className="feature-strip" id="features">
        <div><span className="feature-icon"><BadgeCheck size={19} /></span><span><b>Verified context</b><small>Answers grounded in the records you select.</small></span></div>
        <div><span className="feature-icon"><MessageCircle size={19} /></span><span><b>Speak naturally</b><small>Support in English, Hindi, Tamil and Telugu.</small></span></div>
        <div><span className="feature-icon"><ShieldCheck size={19} /></span><span><b>Clear next steps</b><small>No false promises. You stay in control.</small></span></div>
      </section>
      <section className="how-section" id="how-it-works"><div className="section-kicker">A BETTER WAY FORWARD</div><h2>Understand. Verify. Resolve.</h2><p>From a confusing payment to a clear next step, every time.</p><div className="steps"><div><span>01</span><h3>Tell us what happened</h3><p>Ask in your own words, or pick a transaction to get started.</p></div><div><span>02</span><h3>We check the details</h3><p>ResolveAI uses the available transaction record—never a guess.</p></div><div><span>03</span><h3>Know what to do next</h3><p>Get a simple explanation and a practical path to resolution.</p></div></div></section>
      <footer className="landing-footer"><Link className="brand" to="/"><span className="brand-mark"><ShieldCheck size={18} /></span><span>Resolve<span className="brand-light">AI</span></span></Link><span>Prototype experience · Simulated payment data</span></footer>
    </main>
  );
}

function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const navigate = useNavigate();
  function submitSearch(event) {
    event.preventDefault();
    navigate(`/app/transactions${search.trim() ? `?search=${encodeURIComponent(search.trim())}` : ""}`);
    setSidebarOpen(false);
  }
  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <Link to="/" className="brand sidebar-brand"><span className="brand-mark"><ShieldCheck size={20} /></span><span>Resolve<span className="brand-light">AI</span></span></Link>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav">{navItems.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} onClick={() => setSidebarOpen(false)} className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}><Icon size={18} strokeWidth={1.8} /><span>{label}</span></NavLink>)}</nav>
        <div className="sidebar-bottom">
          <div className="help-card"><span className="help-card-icon"><Headphones size={17} /></span><b>We're here to help</b><p>Get an answer tailored to your payment journey.</p><Link to="/app/assistant">Ask ResolveAI <ArrowRight size={14} /></Link></div>
          <div className="demo-caption"><span className="demo-dot" /> Demo environment</div>
          <div className="profile"><div className="profile-avatar">R</div><div><b>Rukhiya</b><small>Personal account</small></div><MoreHorizontal size={19} className="profile-more" /></div>
        </div>
      </aside>
      {sidebarOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      <main className="main-area">
        <header className="topbar">
          <button className="mobile-menu icon-button" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <div className="breadcrumb">Workspace <span>/</span> <b>Payments</b></div>
          <div className="topbar-actions">
            <form className="global-search" onSubmit={submitSearch}><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search payments" aria-label="Search payments" /></form>
            <div className="notification-wrap">
              <button className="icon-button notification-button" onClick={() => setNotificationsOpen((open) => !open)} aria-label="Notifications" aria-expanded={notificationsOpen}><Bell size={18} /><i /></button>
              {notificationsOpen && <div className="notification-popover"><div className="notification-popover-heading"><b>Payment updates</b><span>DEMO</span></div><Link to="/app/transactions?status=pending" onClick={() => setNotificationsOpen(false)}><Clock3 size={16} /><span><b>2 payments awaiting confirmation</b><small>Check the latest recorded status.</small></span><ArrowRight size={14} /></Link><Link to="/app/refunds" onClick={() => setNotificationsOpen(false)}><ArrowDownLeft size={16} /><span><b>Refunds in progress</b><small>View available refund records.</small></span><ArrowRight size={14} /></Link></div>}
            </div>
            <div className="top-avatar">R</div>
          </div>
        </header>
        <div className="page-content"><Routes><Route path="dashboard" element={<Dashboard />} /><Route path="transactions" element={<TransactionsPage />} /><Route path="transactions/:id" element={<TransactionDetail />} /><Route path="assistant" element={<AssistantPage />} /><Route path="refunds" element={<RefundsPage />} /><Route path="complaints" element={<ComplaintsPage />} /><Route path="*" element={<Navigate to="dashboard" replace />} /></Routes></div>
      </main>
    </div>
  );
}

function PageTitle({ eyebrow, title, description, action }) {
  return <div className="page-title"><div><div className="section-kicker">{eyebrow}</div><h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</div>;
}

function useTransactions(filters = {}) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = () => {
    setLoading(true);
    api.transactions(filters).then(setData).catch((err) => setError(err.message)).finally(() => setLoading(false));
  };
  useEffect(load, [filters.status, filters.search]);
  return { data, loading, error, reload: load };
}

function Dashboard() {
  const { data: transactions, loading, error, reload } = useTransactions();
  const counts = useMemo(() => transactions.reduce((result, transaction) => {
    result.total += 1;
    result[transaction.status] += 1;
    return result;
  }, { total: 0, successful: 0, pending: 0, failed: 0 }), [transactions]);
  return (
    <>
      <PageTitle eyebrow={new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "numeric", month: "long" }).format(new Date()).toUpperCase()} title="Good morning, Rukhiya" description="Here’s a clear view of your recent payment activity." action={<Link className="button button-primary" to="/app/assistant"><Sparkles size={16} /> Ask ResolveAI</Link>} />
      {error && <ErrorNotice message={error} onRetry={reload} />}
      <section className="stat-grid">
        <StatCard label="Total transactions" value={loading ? "—" : counts.total} note="Across your recent activity" icon={WalletCards} />
        <StatCard label="Successful" value={loading ? "—" : counts.successful} note="Payments completed" icon={CheckCircle2} />
        <StatCard label="In progress" value={loading ? "—" : counts.pending} note="Awaiting confirmation" icon={Clock3} tone="amber" />
        <StatCard label="Needs attention" value={loading ? "—" : counts.failed} note="Review resolution options" icon={CircleHelp} tone="red" />
      </section>
      <section className="dashboard-grid">
        <div className="panel recent-panel"><div className="panel-heading"><div><h2>Recent transactions</h2><p>Your latest payment activity</p></div><Link className="link-button" to="/app/transactions">View all <ArrowRight size={15} /></Link></div>
          {loading ? <LoadingRows /> : transactions.length ? <TransactionTable transactions={transactions.slice(0, 5)} /> : <EmptyState title="No transactions yet" body="Your recent activity will appear here." />}
        </div>
        <div className="right-stack">
          <div className="assistant-card"><div className="assistant-card-top"><span className="assistant-orb"><Sparkles size={20} /></span><span className="online-label"><i /> READY TO HELP</span></div><h2>A payment on your mind?</h2><p>Get a clear explanation based on your transaction details and the next step that makes sense.</p><Link to="/app/assistant" className="button button-white">Talk to ResolveAI <ArrowRight size={16} /></Link><div className="assistant-card-foot"><ShieldCheck size={14} /> Private by design · You stay in control</div></div>
          <div className="panel quick-panel"><h3>Quick actions</h3><Link to="/app/refunds"><span className="quick-icon"><ArrowDownLeft size={17} /></span><span><b>Track a refund</b><small>See the latest available progress</small></span><ArrowRight size={15} /></Link><Link to="/app/complaints"><span className="quick-icon"><FileText size={17} /></span><span><b>Raise a complaint</b><small>Tell us what needs attention</small></span><ArrowRight size={15} /></Link></div>
        </div>
      </section>
      <div className="privacy-note"><ShieldCheck size={15} /> This demo uses simulated transaction data. It does not connect to a real Paytm or bank account.</div>
    </>
  );
}

function StatCard({ label, value, note, icon: Icon, tone }) {
  return <div className="stat-card"><div className="stat-top"><span>{label}</span><span className={`stat-icon ${tone || ""}`}><Icon size={17} /></span></div><strong>{value}</strong><small>{note}</small></div>;
}

function LoadingRows() {
  return <div className="loading-list">{[1, 2, 3, 4].map((item) => <div className="loading-row" key={item}><span /><div><i /><i /></div><i /></div>)}</div>;
}

function EmptyState({ title, body }) {
  return <div className="empty-state"><span><Search size={20} /></span><b>{title}</b><p>{body}</p></div>;
}

function TransactionTable({ transactions, compact = false }) {
  const navigate = useNavigate();
  return <div className={`table-wrap ${compact ? "table-compact" : ""}`}><table><thead><tr><th>Merchant</th><th>Reference</th><th>Date</th><th>Method</th><th>Status</th><th className="align-right">Amount</th><th /></tr></thead><tbody>{transactions.map((transaction) => <tr key={transaction.id} role="link" tabIndex={0} onClick={() => navigate(`/app/transactions/${transaction.id}`)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") navigate(`/app/transactions/${transaction.id}`); }}><td><div className="merchant-cell"><span className="merchant-mark">{transaction.merchant.slice(0, 1)}</span><b>{transaction.merchant}</b></div></td><td className="reference-cell">{transaction.id}</td><td>{dateLabel(transaction.created_at)}</td><td>{transaction.payment_method}</td><td><StatusBadge status={transaction.status} /></td><td className="align-right amount-cell">{money(transaction.amount)}</td><td><ArrowRight size={15} className="row-arrow" /></td></tr>)}</tbody></table></div>;
}

function TransactionsPage() {
  const params = new URLSearchParams(window.location.search);
  const [search, setSearch] = useState(params.get("search") || "");
  const [status, setStatus] = useState(params.get("status") || "");
  const { data, loading, error, reload } = useTransactions({ status, search });
  return <>
    <PageTitle eyebrow="PAYMENT ACTIVITY" title="Transactions" description="Search and review the details of your recent payments." />
    <section className="panel transaction-panel">
      <div className="filter-toolbar"><label className="table-search"><Search size={16} /><input placeholder="Search merchant or reference" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label className="select-wrap"><span className="sr-only">Filter by status</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option><option value="successful">Successful</option><option value="pending">Pending</option><option value="failed">Failed</option></select><ChevronDown size={15} /></label><span className="result-count">{loading ? "Loading…" : `${data.length} records`}</span></div>
      {error ? <ErrorNotice message={error} onRetry={reload} /> : loading ? <LoadingRows /> : data.length ? <TransactionTable transactions={data} /> : <EmptyState title="No matching transactions" body="Try another search or clear the selected status filter." />}
    </section>
    <div className="privacy-note"><ShieldCheck size={15} /> Transaction history shown here is simulated demo data.</div>
  </>;
}

function TransactionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [transaction, setTransaction] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.transaction(id).then(setTransaction).catch((err) => setError(err.message)); }, [id]);
  if (error) return <><button className="back-link" onClick={() => navigate("/app/transactions")}><ArrowLeft size={16} /> Transactions</button><ErrorNotice message={error} /></>;
  if (!transaction) return <div className="panel loading-detail"><div className="loading-row"><span /><div><i /><i /></div></div></div>;
  return <>
    <button className="back-link" onClick={() => navigate("/app/transactions")}><ArrowLeft size={16} /> All transactions</button>
    <PageTitle eyebrow="TRANSACTION DETAILS" title={transaction.merchant} description={`${transaction.description} · ${timeLabel(transaction.created_at)}`} action={<StatusBadge status={transaction.status} />} />
    <div className="detail-grid">
      <section className="panel detail-main"><div className="amount-summary"><span>Payment amount</span><strong>{money(transaction.amount)}</strong><span className="reference-cell">{transaction.id}</span></div><div className="detail-list"><DetailRow label="Payment status"><StatusBadge status={transaction.status} /></DetailRow><DetailRow label="Payment method">{transaction.payment_method}</DetailRow><DetailRow label="Transaction date">{timeLabel(transaction.created_at)}</DetailRow><DetailRow label="Bank reference">{transaction.bank_reference || "Not available"}</DetailRow></div>
        <div className="resolution-box"><span className="resolution-icon"><Sparkles size={17} /></span><div><b>What this status means</b><p>{transaction.resolution_guidance.explanation}</p><small><b>Suggested next step:</b> {transaction.resolution_guidance.next_step}</small></div></div>
      </section>
      <section className="panel timeline-panel"><div className="panel-heading"><div><h2>Payment timeline</h2><p>Available status information</p></div></div><div className="timeline">{transaction.timeline.map((item, index) => <div className={`timeline-item ${item.complete ? "complete" : ""}`} key={item.label}><span className="timeline-marker">{item.complete ? <Check size={12} /> : index + 1}</span><div><b>{item.label}</b><small>{item.at ? timeLabel(item.at) : "Waiting for confirmation"}</small></div></div>)}</div>{transaction.refund && <div className="refund-mini"><div><span className="section-kicker">REFUND RECORD</span><StatusBadge status={transaction.refund.status} /></div><b>{money(transaction.refund.amount)}</b><Link to="/app/refunds">Track refund <ArrowRight size={14} /></Link></div>}</section>
    </div>
    <div className="detail-actions"><Link className="button button-primary" to={`/app/assistant?transaction=${transaction.id}`}><Sparkles size={16} /> Ask about this payment</Link><Link className="button button-outline" to="/app/complaints"><Plus size={16} /> Raise a complaint</Link></div>
    <div className="privacy-note"><ShieldCheck size={15} /> This is a simulated record and is not a live payment status check.</div>
  </>;
}

function DetailRow({ label, children }) {
  return <div className="detail-row"><span>{label}</span><b>{children}</b></div>;
}

const languages = [{ value: "en-IN", label: "English" }, { value: "hi-IN", label: "हिन्दी" }, { value: "ta-IN", label: "தமிழ்" }, { value: "te-IN", label: "తెలుగు" }];
const starterQuestions = ["Why is my payment pending?", "I was charged but the order failed", "How long can a refund take?"];
const languageLabel = (value) => languages.find((language) => language.value === value)?.label || "English";
const CHAT_STORAGE_KEY = "resolveai.conversation";
const LANGUAGE_STORAGE_KEY = "resolveai.language";

function initialConversation() {
  try {
    const stored = JSON.parse(localStorage.getItem(CHAT_STORAGE_KEY) || "null");
    if (Array.isArray(stored) && stored.length) {
      return stored.filter((message) => ["user", "assistant"].includes(message.role) && typeof message.text === "string")
        .slice(-80)
        .map((message) => ({
          ...message,
          text: message.text.replace(
            /^Hi .+?, I’m here to help make sense of a payment/,
            "Hi Rukhiya, I’m here to help make sense of a payment",
          ),
          language: languages.some((language) => language.value === message.language) ? message.language : "en-IN",
        }));
    }
  } catch {
    localStorage.removeItem(CHAT_STORAGE_KEY);
  }
  return [{
    role: "assistant",
    text: "Hi Rukhiya, I’m here to help make sense of a payment. Tell me what happened, or choose a transaction below so I can use its recorded details.",
    language: "en-IN",
    createdAt: new Date().toISOString(),
  }];
}

function AssistantPage() {
  const [transactions, setTransactions] = useState([]);
  const [language, setLanguage] = useState(() => {
    const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return languages.some((item) => item.value === stored) ? stored : "en-IN";
  });
  const [transactionId, setTransactionId] = useState("");
  const [messages, setMessages] = useState(initialConversation);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const params = new URLSearchParams(window.location.search);
  useEffect(() => { api.transactions().then((items) => { setTransactions(items); const selected = params.get("transaction"); if (selected && items.some((item) => item.id === selected)) setTransactionId(selected); }).catch((err) => setError(err.message)); }, []);
  useEffect(() => { localStorage.setItem(LANGUAGE_STORAGE_KEY, language); }, [language]);
  useEffect(() => { localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages.slice(-80))); }, [messages]);
  async function sendMessage(text = input) {
    if (!text.trim() || sending) return;
    setError("");
    const userMessage = { role: "user", text: text.trim(), language, createdAt: new Date().toISOString() };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setSending(true);
    try {
      const history = messages.slice(-10).map((message) => ({
        role: message.role,
        content: message.text,
        language: message.language || "en-IN",
      }));
      const result = await api.chat({ message: text.trim(), language, transaction_id: transactionId || null, history });
      if (result.transaction?.id) setTransactionId(result.transaction.id);
      setMessages((current) => [...current, {
        role: "assistant",
        text: result.answer,
        language: result.fallback ? "en-IN" : result.language,
        requestedLanguage: language,
        fallback: result.fallback,
        fallbackMessage: result.fallback_message,
        needsClarification: result.needs_clarification,
        intent: result.intent,
        transaction: result.transaction,
        createdAt: new Date().toISOString(),
      }]);
    } catch (err) {
      setError(err.message);
    } finally { setSending(false); }
  }
  return <>
    <PageTitle eyebrow="HERE WHEN YOU NEED US" title="AI financial assistant" description="A clear answer, grounded in your selected transaction—not a guess." action={<label className="language-select"><span>Language</span><select value={language} onChange={(event) => setLanguage(event.target.value)}>{languages.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select><ChevronDown size={14} /></label>} />
    <section className="chat-layout">
      <div className="panel chat-panel">
        <div className="chat-heading"><span className="chat-avatar"><Sparkles size={18} /></span><div><b>ResolveAI assistant</b><small><i /> Available to help</small></div><span className="chat-secure"><ShieldCheck size={14} /> Private conversation</span></div>
        <div className="chat-messages">
          <div className="chat-day">TODAY</div>
          {messages.map((message, index) => <div className={`message-row ${message.role === "user" ? "message-user" : ""}`} key={`${index}-${message.text.slice(0, 16)}`}>{message.role === "assistant" && <span className="message-avatar"><Sparkles size={13} /></span>}<div className="message-bubble">{message.fallbackMessage && <div className="fallback-note">{message.fallbackMessage}</div>}<p>{message.text}</p>{message.transaction && <div className="verified-context"><BadgeCheck size={14} /> Simulated record · {message.transaction.id} · {message.transaction.merchant} · {money(message.transaction.amount)}</div>}<small>{message.createdAt ? timeLabel(message.createdAt) : "Earlier"} · {languageLabel(message.language)}</small></div></div>)}
          {sending && <div className="message-row"><span className="message-avatar"><Sparkles size={13} /></span><div className="message-bubble typing"><i /><i /><i /></div></div>}
        </div>
        <div className="chat-compose">
          {error && <ErrorNotice message={error} />}
          <div className="chat-context"><label htmlFor="chat-transaction">Use transaction context</label><select id="chat-transaction" value={transactionId} onChange={(event) => setTransactionId(event.target.value)}><option value="">Let ResolveAI find it from my message</option>{transactions.map((transaction) => <option key={transaction.id} value={transaction.id}>{transaction.merchant} · {money(transaction.amount)} · {titleCase(transaction.status)}</option>)}</select><ChevronDown size={15} /></div>
          <form className="chat-input" onSubmit={(event) => { event.preventDefault(); sendMessage(); }}><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Describe what happened with your payment…" maxLength={1500} /><button type="submit" className="send-button" disabled={!input.trim() || sending} aria-label="Send message"><Send size={17} /></button></form>
          <div className="chat-disclaimer"><ShieldCheck size={13} /> Never share your OTP, PIN or password. Transaction context is simulated demo data.</div>
        </div>
      </div>
      <aside className="chat-aside"><div className="panel suggested-panel"><span className="suggested-icon"><MessageCircle size={18} /></span><h3>Not sure where to start?</h3><p>Pick a question to get a helpful starting point.</p><div className="suggestion-list">{starterQuestions.map((question) => <button key={question} onClick={() => sendMessage(question)} disabled={sending}>{question}<ArrowRight size={14} /></button>)}</div></div><div className="assurance-card"><ShieldCheck size={18} /><div><b>Answers with context</b><p>I’ll only explain information available in your selected or matched demo transaction.</p></div></div></aside>
    </section>
  </>;
}

function RefundsPage() {
  const [refunds, setRefunds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lookup, setLookup] = useState("");
  const [result, setResult] = useState(null);
  const [lookupError, setLookupError] = useState("");
  const load = () => { setLoading(true); api.refunds().then(setRefunds).catch((err) => setError(err.message)).finally(() => setLoading(false)); };
  useEffect(load, []);
  async function track(event) {
    event.preventDefault();
    if (!lookup.trim()) return;
    setLookupError(""); setResult(null);
    try { setResult(await api.refund(lookup.trim())); } catch (err) { setLookupError(err.message); }
  }
  return <>
    <PageTitle eyebrow="REFUND PROGRESS" title="Refunds" description="See the refund information available for your transactions." />
    <section className="refund-lookup panel"><div className="lookup-copy"><span className="lookup-icon"><ArrowDownLeft size={20} /></span><div><h2>Track a refund</h2><p>Enter a transaction ID or refund reference to check its latest recorded status.</p></div></div><form onSubmit={track}><label className="sr-only" htmlFor="refund-ref">Transaction or refund reference</label><input id="refund-ref" value={lookup} onChange={(event) => setLookup(event.target.value)} placeholder="e.g. TXN-482801 or RFD-482801" /><button className="button button-primary">Check status <ArrowRight size={15} /></button></form>{lookupError && <ErrorNotice message={lookupError} />}{result && <div className="refund-result"><div><StatusBadge status={result.status} /><b>{result.merchant}</b><span>{result.id} · {money(result.amount)}</span></div><div><small>Expected by</small><b>{result.expected_by ? dateLabel(result.expected_by) : "Not available"}</b></div><span className="refund-result-note">{result.status === "processed" ? "Refund marked as processed in this demo record." : "This demo record shows the refund is still in progress. No completion is guaranteed."}</span></div>}</section>
    <div className="section-heading"><div><h2>Refund records</h2><p>Refund progress linked to a payment record</p></div></div>
    {error ? <ErrorNotice message={error} onRetry={load} /> : loading ? <div className="panel"><LoadingRows /></div> : refunds.length ? <div className="refund-grid">{refunds.map((refund) => <div className="panel refund-card" key={refund.id}><div className="refund-card-top"><span className="refund-card-icon"><ArrowDownLeft size={17} /></span><StatusBadge status={refund.status} /></div><h3>{refund.merchant}</h3><span className="reference-cell">{refund.id} · {refund.transaction_id}</span><strong>{money(refund.amount)}</strong><div className="refund-card-foot"><span>Last updated {dateLabel(refund.updated_at)}</span><span>Expected by {dateLabel(refund.expected_by)}</span></div><div className="refund-progress"><i className={refund.status === "processing" ? "progress-active" : ""} /></div></div>)}</div> : <div className="panel"><EmptyState title="No refunds to track" body="If a refund record becomes available, it will appear here." /></div>}
    <div className="privacy-note"><ShieldCheck size={15} /> Timelines are estimates from simulated records, not bank confirmations.</div>
  </>;
}

function ComplaintsPage() {
  const [transactions, setTransactions] = useState([]);
  const [complaints, setComplaints] = useState([]);
  const [category, setCategory] = useState("Payment not received");
  const [transactionId, setTransactionId] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [lookup, setLookup] = useState("");
  const [tracked, setTracked] = useState(null);
  const [lookupError, setLookupError] = useState("");
  const [tracking, setTracking] = useState(false);
  const load = () => {
    setLoading(true);
    Promise.all([api.transactions(), api.complaints()]).then(([txns, cases]) => { setTransactions(txns); setComplaints(cases); }).catch((err) => setError(err.message)).finally(() => setLoading(false));
  };
  useEffect(load, []);
  async function createComplaint(event) {
    event.preventDefault(); setError(""); setSuccess("");
    setSubmitting(true);
    try {
      const created = await api.createComplaint({ category, transaction_id: transactionId || null, description });
      setSuccess(`Your complaint ${created.id} has been registered. Save this reference to track progress.`);
      setDescription(""); setTracked(created); setLookup(created.id); load();
    } catch (err) { setError(err.message); } finally { setSubmitting(false); }
  }
  async function trackComplaint(event) {
    event.preventDefault(); setTracked(null); setLookupError("");
    if (!lookup.trim()) return;
    setTracking(true);
    try { setTracked(await api.complaint(lookup.trim())); } catch (err) { setLookupError(err.message); }
    finally { setTracking(false); }
  }
  return <>
    <PageTitle eyebrow="WE'RE LISTENING" title="Complaints" description="Register a payment issue or check the progress of a complaint." />
    <div className="complaint-grid">
      <section className="panel complaint-form-panel"><div className="panel-heading"><div><h2>Tell us what happened</h2><p>Share only the details needed to understand your issue.</p></div><span className="form-icon"><FileText size={17} /></span></div>
        <form className="complaint-form" onSubmit={createComplaint}>
          <label>Issue category<select value={category} onChange={(event) => setCategory(event.target.value)}><option>Payment not received</option><option>Money debited, order failed</option><option>Refund delayed</option><option>Incorrect transaction status</option><option>Other payment issue</option></select></label>
          <label>Related transaction <select value={transactionId} onChange={(event) => setTransactionId(event.target.value)}><option value="">Choose a transaction (optional)</option>{transactions.map((transaction) => <option key={transaction.id} value={transaction.id}>{transaction.id} · {transaction.merchant} · {money(transaction.amount)}</option>)}</select></label>
          <label>What happened? <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Describe the issue. Please don't include OTPs, PINs or passwords." minLength={10} maxLength={1000} required /></label>
          <div className="character-count">{description.length}/1000 characters</div>
          {error && <ErrorNotice message={error} onRetry={load} />}
          {success && <div className="notice notice-success"><CheckCircle2 size={17} />{success}</div>}
          <button className="button button-primary" disabled={submitting || loading || description.trim().length < 10}>{submitting ? "Registering…" : "Submit complaint"} <ArrowRight size={15} /></button>
          <small className="form-footnote"><ShieldCheck size={13} /> A reference will be generated so you can check progress later.</small>
        </form>
      </section>
      <div className="complaint-side">
        <section className="panel tracking-panel"><div className="panel-heading"><div><h2>Track a complaint</h2><p>Enter the reference from your confirmation.</p></div></div><form onSubmit={trackComplaint} className="track-form"><input value={lookup} onChange={(event) => setLookup(event.target.value)} placeholder="e.g. CMP-A1B2C3D4" aria-label="Complaint reference" /><button className="button button-primary" aria-label="Track complaint" disabled={tracking || !lookup.trim()}>{tracking ? <span className="button-spinner" /> : <ArrowRight size={16} />}</button></form>{lookupError && <ErrorNotice message={lookupError} />}{tracked && <ComplaintProgress complaint={tracked} />}</section>
        <section className="panel cases-panel"><div className="panel-heading"><div><h2>Your complaints</h2><p>Recent cases from this demo account</p></div></div>{loading ? <LoadingRows /> : complaints.length ? complaints.slice(0, 3).map((complaint) => <button className="case-row" key={complaint.id} onClick={() => { setLookup(complaint.id); setTracked(complaint); setLookupError(""); }}><span className="case-icon"><FileText size={16} /></span><span><b>{complaint.category}</b><small>{complaint.id} · {dateLabel(complaint.created_at)}</small></span><StatusBadge status={complaint.status} /></button>) : <EmptyState title="No complaints yet" body="Registered complaints will be listed here." />}</section>
      </div>
    </div>
    <div className="privacy-note"><ShieldCheck size={15} /> Never include your OTP, PIN, password or full bank/card details in a complaint.</div>
  </>;
}

function ComplaintProgress({ complaint }) {
  return <div className="tracked-case">
    <div className="tracked-head"><div><span className="section-kicker">DEMO COMPLAINT</span><b>{complaint.id}</b></div><StatusBadge status={complaint.status} /></div>
    <div className="complaint-current"><b>{complaint.status_label}</b><p>{complaint.status_explanation}</p></div>
    <p>{complaint.description}</p>
    <div className="mini-timeline">{complaint.timeline.map((item, index) => <div key={`${item.status}-${item.at || "pending"}-${index}`} className={`${item.complete ? "complete" : ""} ${item.current ? "current" : ""}`}><i /><span><b>{item.label}</b><small>{item.at ? timeLabel(item.at) : item.skipped ? "No update recorded" : "Not reached yet"}{item.current && item.at ? " · Current" : ""}</small></span></div>)}</div>
    <small className="complaint-demo-note">Demo progress only. No real bank, merchant, or Paytm support team is investigating this complaint.</small>
  </div>;
}

function App() {
  return <BrowserRouter><Routes><Route path="/" element={<LandingPage />} /><Route path="/app/*" element={<AppLayout />} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></BrowserRouter>;
}

export default App;
