---
trigger: always_on
---

# Cursor Rules for AI Programmers

These rules outline best practices for working on **Green-Ding**, a Next.js/TypeScript project that integrates Supabase, Tailwind CSS, and Playwright. They are written for AI programmers and highlight common mistakes to avoid while promoting maintainable code.

## 1. General Guidelines
- Keep the codebase readable and consistent. Always run Prettier and ESLint.
- Use TypeScript for all new frontend and backend logic.
- Document complex functions with JSDoc comments and keep them small.
- Validate environment variables with a utility (e.g. `zod`) so deployments fail fast when misconfigured.
- Update or add tests whenever you modify features.
- To stay up-to-date on documentation of frameworks, use context7. 
- When appropriate, use firecrawl to scrape websites and return llm friendly content. 

## 2. Project Structure
- The main application lives in `green-ding/`.
- Frontend code resides under `green-ding/src/` using the Next.js App Router.
- Reusable components go in `src/components/` with descriptive names.
- Backend utilities (including the Supabase client) are in `src/lib/`.

## 3. Next.js and React
- Use functional components with hooks; avoid class components.
- Prefer server components for data fetching and keep client components small.
- **Do not call data-fetching functions inside `useEffect` when a server component can do it.**
- Always use `async/await` with data-loading functions, and handle errors explicitly.
- Respect the App Router layout and avoid custom routing logic unless required.
- For client components, include `"use client"` at the top and avoid server-only modules.
- Use `next/link` and `next/router` for internal navigation rather than direct `window.location` calls.
- Split complex logic into custom hooks located in `src/hooks/`.
- Prefer dynamic imports for large libraries or rarely used components.

## 4. TypeScript
- Enable strict type checking. Always specify explicit types for function inputs and outputs.
- Use interfaces or type aliases for complex objects (e.g., `Profile`, `Course`).
- Avoid `any` and `unknown` unless absolutely necessary. Document any exceptions.
- Use generics for reusable utility functions instead of broad types.
- Remember that `null` and `undefined` are different—handle both where applicable.
- Use `zod` schemas to validate data from APIs and derive types via `z.infer`.
- Keep shared types in `src/types/` so both client and server code reuse them.

## 5. Supabase
- Instantiate Supabase clients via `src/lib/supabase/client.ts` only and keep that module small.
- Keep queries parameterized to prevent SQL injection and always prefer the `supabase.from(...).select()` API over raw SQL when possible.
- Handle Supabase errors via `.throwOnError()` or explicit checks; log errors with context for easier debugging.
- **Never expose service keys or admin tokens in client-side code.** Use environment variables on the server only.
- Respect row-level security policies when designing database operations.
- Centralize database access logic in `src/lib/supabase` to avoid duplicate queries across the codebase.

## 6. Tailwind CSS and Styling
- Compose styles using Tailwind utility classes and avoid arbitrary values when standard classes exist.
- Keep class names short and consistent, ordering from layout to modifiers.
- Co-locate styles with components whenever possible for clarity.
- Use shadcn/ui components as a starting point and extend them carefully (see `.windsurfrules` for details).
- Group repeated class sets into helper functions using `clsx` or `cva` to reduce duplication.
- Limit global CSS to layout resets and font declarations; prefer component-level styling with Tailwind.

## 7. Playwright and Web Scraping
- Scraping logic and background jobs live under `tee-time-checker/`.
- Respect target sites’ `robots.txt` and apply sensible delays to avoid rate limits.
- Always close browsers and contexts in Playwright to prevent memory leaks.
- Store scraped data or job results in Supabase using the appropriate service functions.
- Capture screenshots or HTML dumps on failures to make debugging easier.
- Keep scraping logic modular so different sites can reuse the same login or parsing routines.


## 8. Git Practices
- Commit focused changes with descriptive messages.
- Keep the main branch stable; create feature branches for larger work.
- Reference relevant issues in commit messages when possible.
- Open pull requests summarizing changes and describing testing steps.

Following these rules will help keep the project maintainable and accessible to all contributors for the long term.