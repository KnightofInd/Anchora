"use client";

import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminUsersApi, authApi, getApiErrorMessage } from "@/lib/api";
import { EmptyState, ErrorState, LoadingState } from "@/app/dashboard/_components/query-states";
import { useToast } from "@/app/_components/toast";

interface Role {
  id: string;
  name: string;
}

interface UserRecord {
  id: string;
  email: string;
  full_name: string;
  role_id: string;
  role_name: string;
  is_active: boolean;
  created_at: string;
}

export default function UsersPage() {
  const qc = useQueryClient();
  const { showToast } = useToast();

  const [form, setForm] = useState({
    email: "",
    full_name: "",
    password: "",
    role_id: "",
    is_active: true,
  });

  const { data: meData, isLoading: meLoading } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => authApi.me(),
  });

  const me = meData?.data as { role_name?: string } | undefined;
  const isAdmin = (me?.role_name ?? "").toLowerCase() === "admin";

  const {
    data: rolesData,
    isLoading: rolesLoading,
    isError: rolesError,
    error: rolesErrorData,
    refetch: refetchRoles,
  } = useQuery({
    queryKey: ["admin", "roles"],
    queryFn: () => adminUsersApi.listRoles(),
    enabled: isAdmin,
  });

  const {
    data: usersData,
    isLoading: usersLoading,
    isError: usersError,
    error: usersErrorData,
    refetch: refetchUsers,
  } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => adminUsersApi.listUsers(),
    enabled: isAdmin,
  });

  const roles = useMemo<Role[]>(() => rolesData?.data ?? [], [rolesData]);
  const users = useMemo<UserRecord[]>(() => usersData?.data ?? [], [usersData]);

  const createUserMutation = useMutation({
    mutationFn: () => adminUsersApi.createUser(form),
    onSuccess: () => {
      setForm({ email: "", full_name: "", password: "", role_id: "", is_active: true });
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
      showToast({
        variant: "success",
        title: "User created",
        message: "The new user has been added successfully.",
      });
    },
    onError: (err: unknown) => {
      showToast({
        variant: "error",
        title: "Create failed",
        message: getApiErrorMessage(err, "Unable to create user."),
      });
    },
  });

  const updateUserMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { role_id?: string; is_active?: boolean } }) =>
      adminUsersApi.updateUser(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
      showToast({
        variant: "success",
        title: "User updated",
        message: "User settings were saved.",
      });
    },
    onError: (err: unknown) => {
      showToast({
        variant: "error",
        title: "Update failed",
        message: getApiErrorMessage(err, "Unable to update user."),
      });
    },
  });

  function handleCreateUser(event: FormEvent) {
    event.preventDefault();
    if (!form.role_id) {
      showToast({ variant: "error", title: "Role required", message: "Please choose a role." });
      return;
    }
    createUserMutation.mutate();
  }

  if (meLoading) {
    return <div className="p-6"><LoadingState label="Checking access..." /></div>;
  }

  if (!isAdmin) {
    return (
      <div className="p-6">
        <ErrorState
          title="Admin access required"
          message="Only admins can access user management."
        />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">User Management</h1>
        <p className="text-sm text-slate-500 mt-0.5">Create users and manage roles and account status.</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-6">
        <form onSubmit={handleCreateUser} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
          <h2 className="text-sm font-semibold text-slate-800">Create User</h2>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Full Name</label>
            <input
              required
              value={form.full_name}
              onChange={(e) => setForm((prev) => ({ ...prev, full_name: e.target.value }))}
              className="w-full h-10 px-3 rounded-lg border border-slate-300 text-sm"
              placeholder="Enter full name"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Email</label>
            <input
              required
              type="email"
              value={form.email}
              onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
              className="w-full h-10 px-3 rounded-lg border border-slate-300 text-sm"
              placeholder="name@anchora.dev"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Temporary Password</label>
            <input
              required
              type="password"
              minLength={8}
              value={form.password}
              onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
              className="w-full h-10 px-3 rounded-lg border border-slate-300 text-sm"
              placeholder="Minimum 8 characters"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Role</label>
            {rolesLoading ? (
              <LoadingState label="Loading roles..." />
            ) : rolesError ? (
              <ErrorState
                title="Could not load roles"
                message={getApiErrorMessage(rolesErrorData, "Failed to load roles.")}
                onRetry={() => {
                  void refetchRoles();
                }}
              />
            ) : (
              <select
                required
                value={form.role_id}
                onChange={(e) => setForm((prev) => ({ ...prev, role_id: e.target.value }))}
                className="w-full h-10 px-3 rounded-lg border border-slate-300 text-sm bg-white"
              >
                <option value="">Select role</option>
                {roles.map((role) => (
                  <option key={role.id} value={role.id}>{role.name}</option>
                ))}
              </select>
            )}
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm((prev) => ({ ...prev, is_active: e.target.checked }))}
            />
            Active account
          </label>

          <button
            type="submit"
            disabled={createUserMutation.isPending || rolesLoading}
            className="w-full h-10 rounded-xl bg-[#1e3fae] text-white text-sm font-semibold disabled:opacity-50"
          >
            {createUserMutation.isPending ? "Creating..." : "Create User"}
          </button>
        </form>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-800">All Users</h2>
            <span className="text-xs text-slate-400">{users.length} users</span>
          </div>

          {usersLoading ? (
            <div className="p-4"><LoadingState label="Loading users..." /></div>
          ) : usersError ? (
            <div className="p-4">
              <ErrorState
                title="Could not load users"
                message={getApiErrorMessage(usersErrorData, "Failed to load users.")}
                onRetry={() => {
                  void refetchUsers();
                }}
              />
            </div>
          ) : users.length === 0 ? (
            <div className="p-4">
              <EmptyState icon="group" title="No users" description="Create your first user from the form." />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[760px]">
                <thead className="bg-slate-50 border-b border-slate-100">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">User</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">Role</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">Created</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td className="px-4 py-3">
                        <p className="text-sm font-semibold text-slate-800">{user.full_name}</p>
                        <p className="text-xs text-slate-400">{user.email}</p>
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={user.role_id}
                          onChange={(e) => {
                            updateUserMutation.mutate({ id: user.id, payload: { role_id: e.target.value } });
                          }}
                          className="h-8 px-2 rounded-md border border-slate-300 text-xs bg-white"
                        >
                          {roles.map((role) => (
                            <option key={role.id} value={role.id}>{role.name}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${user.is_active ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-600"}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${user.is_active ? "bg-green-500" : "bg-slate-400"}`} />
                          {user.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">{new Date(user.created_at).toLocaleDateString()}</td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => {
                            updateUserMutation.mutate({
                              id: user.id,
                              payload: { is_active: !user.is_active },
                            });
                          }}
                          disabled={updateUserMutation.isPending}
                          className="h-8 px-2.5 rounded-md border border-slate-200 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                        >
                          {user.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
