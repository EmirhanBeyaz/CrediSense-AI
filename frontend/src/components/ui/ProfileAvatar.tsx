import type { User } from "@/types";

type ProfileAvatarProps = {
  user: User;
  size?: "sm" | "lg";
  editable?: boolean;
  loading?: boolean;
  onImageSelected?: (file: File) => void;
};

const sizeClasses = {
  sm: "h-11 w-11",
  lg: "h-32 w-32",
};

export function ProfileAvatar({
  user,
  size = "sm",
  editable = false,
  loading = false,
  onImageSelected,
}: ProfileAvatarProps) {
  const imageUrl = profileImageUrl(user);
  const inputId = `profile-avatar-${user.id}-${size}`;

  return (
    <div className="grid justify-items-center">
      <label
        className={`group relative block ${sizeClasses[size]} overflow-hidden rounded-full border border-white/15 bg-[#e9e9e9] shadow-inner ${
          editable ? "cursor-pointer" : ""
        }`}
        htmlFor={editable ? inputId : undefined}
      >
        {imageUrl ? (
          <img alt={`${user.fullName} profil resmi`} className="h-full w-full object-cover" src={imageUrl} />
        ) : (
          <DefaultAvatarShape />
        )}
        {editable ? (
          <span className="absolute inset-0 grid place-items-center bg-black/0 text-transparent transition group-hover:bg-black/45 group-hover:text-white">
            <span className="material-symbols-outlined text-3xl">photo_camera</span>
          </span>
        ) : null}
      </label>
      {editable ? (
        <>
          <input
            accept="image/*"
            className="sr-only"
            disabled={loading}
            id={inputId}
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file && onImageSelected) {
                onImageSelected(file);
              }
            }}
            type="file"
          />
        </>
      ) : null}
    </div>
  );
}

export function profileImageUrl(user: User): string {
  const imageUrl = String(user.profile?.profile_image || "").trim();
  return imageUrl.startsWith("data:image/") ? imageUrl : "";
}

function DefaultAvatarShape() {
  return (
    <span aria-hidden="true" className="absolute inset-0 block overflow-hidden rounded-full bg-[#e9e9e9]">
      <span className="absolute left-1/2 top-[18%] h-[31%] w-[31%] -translate-x-1/2 rounded-full bg-[#9ea4a1] ring-1 ring-black/20" />
      <span className="absolute -bottom-[11%] left-1/2 h-[52%] w-[80%] -translate-x-1/2 rounded-t-[50%] bg-[#9ea4a1] ring-1 ring-black/20" />
    </span>
  );
}
