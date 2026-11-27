import { SignUp } from "@clerk/nextjs";
import AuthPageShell from "@/components/AuthPageShell";
import { clerkAppearance } from "@/lib/clerkAppearance";

export default function SignUpPage() {
  return (
    <AuthPageShell
      eyebrow="START WITH A CONVERSATION"
      heading="Create your space."
      subheading="Practice in here, perform out there."
    >
      <SignUp appearance={clerkAppearance} />
    </AuthPageShell>
  );
}
