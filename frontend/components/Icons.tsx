// Figma design icons, inlined to match the project's existing SVG-as-JSX pattern.
// Paths come from the "Simulation — Left guidance" frame.

type IconProps = {
  className?: string;
  size?: number;
};

function Icon({
  size,
  className,
  viewBox,
  strokeWidth = 1.6,
  children,
}: IconProps & { viewBox: string; strokeWidth?: number; children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox={viewBox}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function HomeIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 24 24" strokeWidth={1.65}>
      <path d="M3 10L12 3L21 10V21H14V13H10V21H3V10Z" />
    </Icon>
  );
}

export function ChatIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 24 24" strokeWidth={1.65}>
      <path d="M6 4H18C19.0609 4 20.0783 4.42143 20.8284 5.17157C21.5786 5.92172 22 6.93913 22 8V15C22 16.0609 21.5786 17.0783 20.8284 17.8284C20.0783 18.5786 19.0609 19 18 19H9L4 22L5 18C4.11992 17.7732 3.34329 17.2536 2.798 16.5265C2.25271 15.7994 1.97126 14.9084 2 14V8C2 6.93913 2.42143 5.92172 3.17157 5.17157C3.92172 4.42143 4.93913 4 6 4Z" />
      <path d="M7 11H7.01M12 11H12.01M17 11H17.01" />
    </Icon>
  );
}

export function ChartIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 24 24" strokeWidth={1.65}>
      <path d="M3 2V21H22M8 16V11M13 16V6M18 16V9" />
    </Icon>
  );
}

export function ExternalIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 20 20" strokeWidth={1.375}>
      <path d="M3.33333 16.6667L16.6667 3.33333M16.6667 11.6667V3.33333H8.33333" />
    </Icon>
  );
}

export function ArrowIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 20 20" strokeWidth={1.375}>
      <path d="M3.33333 10H15.8333M10.8333 15L15.8333 10L10.8333 5" />
    </Icon>
  );
}

export function HelpIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 22 22" strokeWidth={1.5125}>
      <path d="M19.25 11C19.25 15.5563 15.5563 19.25 11 19.25C6.44365 19.25 2.75 15.5563 2.75 11C2.75 6.44365 6.44365 2.75 11 2.75C15.5563 2.75 19.25 6.44365 19.25 11Z" />
      <path d="M8.25 7.33333C8.21446 6.86756 8.29815 6.40041 8.49318 5.97594C8.68821 5.55147 8.98816 5.18368 9.36472 4.90726C9.74129 4.63083 10.1821 4.45489 10.6455 4.39602C11.1089 4.33715 11.5796 4.3973 12.0134 4.57078C12.4471 4.74427 12.8294 5.02538 13.1244 5.3876C13.4194 5.74982 13.6172 6.18121 13.6993 6.64108C13.7813 7.10095 13.7449 7.57414 13.5934 8.01601C13.4419 8.45789 13.1803 8.85389 12.8333 9.16667C11 10.0833 11 11 11 12.8333M11 15.5833V15.5925" />
    </Icon>
  );
}

export function LogoutIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 20 20" strokeWidth={1.375}>
      <path d="M7.5 2.5H2.5V17.5H7.5M7.5 10H17.5M13.3333 14.1667L17.5 10L13.3333 5.83333" />
    </Icon>
  );
}

export function ClockIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 22 22" strokeWidth={1.46667}>
      <path d="M19.25 11C19.25 15.5563 15.5563 19.25 11 19.25C6.44365 19.25 2.75 15.5563 2.75 11C2.75 6.44365 6.44365 2.75 11 2.75C15.5563 2.75 19.25 6.44365 19.25 11Z" />
      <path d="M11 5.5V11L14.6667 12.8333" />
    </Icon>
  );
}

export function PauseIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 20 20" strokeWidth={1.33333}>
      <path d="M6.66667 4.16667V15.8333M13.3333 4.16667V15.8333" />
    </Icon>
  );
}

export function SparklesIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 24 24" strokeWidth={1.6}>
      <path d="M10 3L12.5 9.5L19 12L12.5 14.5L10 21L7.5 14.5L1 12L7.5 9.5L10 3ZM19 2L20 5L23 6L20 7L19 10L18 7L15 6L18 5L19 2Z" />
    </Icon>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 18 18" strokeWidth={1.2}>
      <path d="M3.75 9L6.75 12L15 3.75" />
    </Icon>
  );
}

export function KeyboardIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 20 20" strokeWidth={1.33333}>
      <path d="M4.16667 4.16667H15.8333C17.214 4.16667 18.3333 5.28596 18.3333 6.66667V13.3333C18.3333 14.714 17.214 15.8333 15.8333 15.8333H4.16667C2.78595 15.8333 1.66667 14.714 1.66667 13.3333V6.66667C1.66667 5.28596 2.78595 4.16667 4.16667 4.16667Z" />
      <path d="M5 7.5H5.00833M8.33333 7.5H8.34167M11.6667 7.5H11.675M15 7.5H15.0083M5 10H5.00833M8.33333 10H8.34167M11.6667 10H11.675M15 10H15.0083M6.66667 13.3333H13.3333" />
    </Icon>
  );
}

export function MicIcon(props: IconProps) {
  return (
    <Icon {...props} viewBox="0 0 20 20" strokeWidth={1.33333}>
      <path d="M10 1.66667C11.3807 1.66667 12.5 2.78595 12.5 4.16667V10C12.5 11.3807 11.3807 12.5 10 12.5C8.61929 12.5 7.5 11.3807 7.5 10V4.16667C7.5 2.78595 8.61929 1.66667 10 1.66667Z" />
      <path d="M4.16667 8.33333V10C4.16667 11.5471 4.78125 13.0308 5.87521 14.1248C6.96917 15.2188 8.4529 15.8333 10 15.8333M10 15.8333C11.5471 15.8333 13.0308 15.2188 14.1248 14.1248C15.2188 13.0308 15.8333 11.5471 15.8333 10V8.33333M10 15.8333V18.3333M10 18.3333H6.66667M10 18.3333H13.3333" />
    </Icon>
  );
}

export function StatusDot({ className }: { className?: string }) {
  return (
    <svg width="6" height="6" viewBox="0 0 6 6" className={className} aria-hidden="true">
      <circle cx="3" cy="3" r="3" fill="currentColor" />
    </svg>
  );
}
