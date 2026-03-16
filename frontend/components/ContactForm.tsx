// Interactive contact form with backend integration for partnership and investor inquiries.
"use client";

import { useState } from "react";
import { submitContactInquiry } from "@/lib/api";
import { ContactInquiry } from "@/lib/types";
import { BrandLogo } from "@/components/BrandLogo";

const initialPayload: ContactInquiry = {
  name: "",
  email: "",
  interest: "investor_relations",
  message: ""
};

export function ContactForm() {
  const [payload, setPayload] = useState<ContactInquiry>(initialPayload);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      await submitContactInquiry(payload);
      setMessage("Inquiry received. SolarShare team will follow up shortly.");
      setPayload(initialPayload);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to submit inquiry.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card">
      <div className="mb-2 inline-flex rounded-xl border border-solarBlue-100 bg-solarBlue-50 px-2 py-1">
        <BrandLogo full className="scale-[0.62] origin-left" />
      </div>
      <label className="grid gap-2 text-sm font-semibold text-solarBlue-900/80">
        Name
        <input
          value={payload.name}
          onChange={(event) => setPayload((prev) => ({ ...prev, name: event.target.value }))}
          minLength={2}
          maxLength={120}
          required
          className="rounded-xl border border-solarBlue-100 px-4 py-3 outline-none ring-solarBlue-200 focus:ring"
        />
      </label>

      <label className="grid gap-2 text-sm font-semibold text-solarBlue-900/80">
        Email
        <input
          type="email"
          value={payload.email}
          onChange={(event) => setPayload((prev) => ({ ...prev, email: event.target.value }))}
          required
          className="rounded-xl border border-solarBlue-100 px-4 py-3 outline-none ring-solarBlue-200 focus:ring"
        />
      </label>

      <label className="grid gap-2 text-sm font-semibold text-solarBlue-900/80">
        Inquiry Type
        <select
          value={payload.interest}
          onChange={(event) =>
            setPayload((prev) => ({ ...prev, interest: event.target.value as ContactInquiry["interest"] }))
          }
          className="rounded-xl border border-solarBlue-100 px-4 py-3 outline-none ring-solarBlue-200 focus:ring"
        >
          <option value="investor_relations">Investor Relations</option>
          <option value="partnership">Partnership</option>
          <option value="methodology_question">Methodology Question</option>
          <option value="customer_support">Customer Support</option>
          <option value="other">Other</option>
        </select>
      </label>

      <label className="grid gap-2 text-sm font-semibold text-solarBlue-900/80">
        Message
        <textarea
          value={payload.message}
          onChange={(event) => setPayload((prev) => ({ ...prev, message: event.target.value }))}
          minLength={10}
          maxLength={1000}
          required
          rows={6}
          className="rounded-xl border border-solarBlue-100 px-4 py-3 outline-none ring-solarBlue-200 focus:ring"
        />
      </label>

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-xl bg-solarBlue-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-solarBlue-900 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {loading ? "Submitting..." : "Submit Inquiry"}
      </button>

      {message ? <p className="rounded-xl bg-energyGreen-100 px-3 py-2 text-sm font-semibold text-energyGreen-700">{message}</p> : null}
      {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm font-semibold text-red-600">{error}</p> : null}
    </form>
  );
}
