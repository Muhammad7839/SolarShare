// Demo request form that captures product walkthrough leads without duplicate submissions.
"use client";

import { useRef, useState } from "react";
import { createIdempotencyKey, submitDemoRequest } from "@/lib/api";
import { DemoRequest } from "@/lib/types";

const initialPayload: DemoRequest = {
  name: "",
  email: "",
  organization: "",
  message: ""
};

export function DemoRequestForm() {
  const [payload, setPayload] = useState<DemoRequest>(initialPayload);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const submitLockRef = useRef(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitLockRef.current) {
      return;
    }

    submitLockRef.current = true;
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      await submitDemoRequest(payload, { idempotencyKey: createIdempotencyKey("demo") });
      setMessage("Demo request received. SolarShare team will follow up shortly.");
      setPayload(initialPayload);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to submit demo request.");
    } finally {
      submitLockRef.current = false;
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-3xl border border-solarBlue-100 bg-white p-6 shadow-card">
      <h3 className="text-xl font-semibold text-solarBlue-900">Request a Demo</h3>

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
        Organization (optional)
        <input
          value={payload.organization || ""}
          onChange={(event) => setPayload((prev) => ({ ...prev, organization: event.target.value }))}
          maxLength={160}
          className="rounded-xl border border-solarBlue-100 px-4 py-3 outline-none ring-solarBlue-200 focus:ring"
        />
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
        {loading ? "Submitting..." : "Submit Demo Request"}
      </button>

      {message ? <p className="rounded-xl bg-energyGreen-100 px-3 py-2 text-sm font-semibold text-energyGreen-700">{message}</p> : null}
      {error ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm font-semibold text-red-600">{error}</p> : null}
    </form>
  );
}
