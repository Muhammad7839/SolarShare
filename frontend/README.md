# SolarShare Frontend (Next.js 2026)

This is the production-oriented web frontend for SolarShare.

## Stack
- Next.js (App Router)
- React
- Tailwind CSS
- Framer Motion
- Lucide Icons

## Pages
- `/` Home
- `/product`
- `/how-it-works`
- `/technology`
- `/pricing`
- `/about`
- `/contact`

## API Integration
The product and contact flows call FastAPI backend endpoints:
- `POST /live-comparison`
- `POST /contact-inquiries`

Set backend base URL in `.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Run

```bash
npm install
npm run dev
```

Frontend default: `http://127.0.0.1:3000`

## Production Deploy (Vercel)

1. Import this repository in Vercel.
2. Set root directory to `frontend`.
3. Set `NEXT_PUBLIC_API_BASE_URL` to your Render backend URL.
4. Deploy.
