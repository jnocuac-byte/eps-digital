# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Primary:** Colombian EPS-affiliated patients (young adults to seniors, many on mobile). They need to schedule medical appointments quickly and reliably through natural conversation with an AI assistant.

**Secondary:** EPS administrators (manage doctor availability, service catalog, reports, user accounts) and doctors (agenda, appointments, clinical history, notifications). Admin and doctor areas should stay clear and functional; the design effort prioritizes the patient experience.

## Product Purpose

EPS Digital enables Colombian EPS members to book medical appointments through an AI-powered assistant (EPSIA) that understands natural language, matches patients with the right specialist, checks real-time availability, and completes the booking -- replacing manual phone calls and in-person queues. Success is a confirmed appointment booked in under two minutes with zero confusion.

## Positioning

EPS Digital is the only Colombian EPS platform where patients book appointments through conversational AI rather than forms or phone trees. The AI assistant (EPSIA) handles the entire flow -- understanding symptoms, recommending specialties, and scheduling -- while the backend's 6-service architecture ensures real-time availability, secure data handling, and reliable notifications.

## Operating Context

- Patients interact primarily on mobile devices in Spanish (Colombia).
- The core workflow: patient describes what they need -> EPSIA classifies the request -> recommends specialists -> checks availability -> books the appointment -> sends confirmation.
- Secondary workflow: patients browse the doctor/specialty catalog and book manually.
- Administrators and doctors access web dashboards for management tasks.
- Appointment slots are tied to real doctor schedules across multiple EPS locations (sedes).
- Notifications arrive via email and in-app bell (for doctors).
- Timezone: America/Bogota (critical for appointment logic).

## Capabilities and Constraints

**Confirmed functionality:**
- AI chatbot (EPSIA) for natural language appointment booking
- Manual appointment browsing and booking
- Doctor, specialty, and location catalog
- Patient profile and medical information management
- Doctor availability management and schedule views
- Appointment history, status tracking, and rescheduling
- Email notifications and in-app notifications for doctors
- Multi-service architecture (6 FastAPI microservices + React SPA)

**Technical constraints:**
- Existing React + Vite + TypeScript + Tailwind + shadcn/ui frontend
- Only visual design may change; do NOT modify logic, API calls, stores, routes, or form validation
- Backend: Python/FastAPI microservices with PostgreSQL databases

**Regulatory constraints:**
- All UI text in Spanish (Colombia).
- WCAG 2.1 AA compliance (contrast >= 4.5:1, readable font sizes, keyboard navigation, focus states).
- Calm, trustworthy tone appropriate for healthcare.
- Ley 1581/2012 (personal data protection).
- Ley 2015/2020 (interoperable clinical history).
- ISO 27799: do not expose sensitive medical data carelessly in the UI; keep consent and privacy messaging prominent.

## Brand Commitments

- Product name: "EPS Digital".
- AI assistant name: "EPSIA".
- Documented palette: primary deep navy #2B3E59 (navbar, primary buttons), white background, card background #F5F5F5, text #333333 and #666666.
- Documented typography: Inter (titles, navigation) and Roboto (body, buttons).
- The navy (#2B3E59) is the brand anchor and must be preserved.
- Fonts, secondary/accent colors are open to change if it improves the result.
- Voice: calm, trustworthy, healthcare-appropriate.

## Evidence on Hand

- Full architecture documentation: AGENTS.md, backend_context.md, frontend_context.md, e2e_integration_context.md.
- Working React frontend with existing UI (login, chat, dashboards, catalogs).
- 6 backend microservices with real APIs and PostgreSQL databases.
- No formal design system or component library beyond shadcn/ui base.

## Product Principles

1. **Patient-first:** Prioritize the patient booking experience above all other interfaces.
2. **AI-native:** EPSIA is the primary booking interface, not an afterthought bolted onto a form.
3. **Trustworthy healthcare:** Every interaction must feel calm, reliable, and secure.
4. **Accessible by default:** WCAG 2.1 AA is the floor, not the ceiling.
5. **Visual only:** Changes are cosmetic; logic, API calls, stores, routes, and validation are untouched.
