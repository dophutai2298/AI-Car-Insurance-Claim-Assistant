export type UserRole = "ADMIN" | "ADJUSTER";

export type AuthUser = {
  email: string;
  full_name: string;
  role: UserRole;
};

export type AuthSession = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type LoginCredentials = {
  email: string;
  password: string;
};
