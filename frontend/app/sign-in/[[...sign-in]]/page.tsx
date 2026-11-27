import { SignIn } from "@clerk/nextjs";
import AuthPageShell from "@/components/AuthPageShell";
import { clerkAppearance } from "@/lib/clerkAppearance";

export default function SignInPage() {
  return (
    <AuthPageShell
      eyebrow="WE’RE HAPPY TO SEE YOU"
      heading="Welcome back."
      subheading="Pick up where you left off."
    >
      <SignIn appearance={clerkAppearance} />
    </AuthPageShell>
  );
}
