import { beforeEach, describe, expect, it, vi } from "vitest";

const createMockTableClient = () => {
  const client: any = {};
  client.insert = vi.fn(() => Promise.resolve({ data: [], error: null }));
  client.upsert = vi.fn(() => Promise.resolve({ data: [], error: null }));
  client.update = vi.fn(() => client);
  client.delete = vi.fn(() => client);
  client.match = vi.fn(() => client);
  client.eq = vi.fn(() => client);
  client.select = vi.fn(() => client);
  return client;
};

const createMockStorageClient = () => ({
  upload: vi.fn(() => Promise.resolve({ data: null, error: null })),
  list: vi.fn(() => Promise.resolve({ data: [], error: null })),
});

const getSupabaseMock = () =>
  supabase as unknown as {
    auth: {
      signUp: ReturnType<typeof vi.fn>;
      signInWithPassword: ReturnType<typeof vi.fn>;
      signOut: ReturnType<typeof vi.fn>;
    };
    storage: {
      createBucket: ReturnType<typeof vi.fn>;
      from: ReturnType<typeof vi.fn>;
    };
    from: ReturnType<typeof vi.fn>;
  };

vi.mock("./supabaseClient", () => {
  const auth = {
    signUp: vi.fn(),
    signInWithPassword: vi.fn(),
    signOut: vi.fn(),
  };
  const storageFrom = vi.fn();
  const storage = {
    createBucket: vi.fn(),
    from: storageFrom,
  };
  const from = vi.fn();
  const supabaseMock = { auth, storage, from };
  return { supabase: supabaseMock };
});

import { supabase } from "./supabaseClient";
import {
  createStorageBucket,
  deleteRecords,
  insertRecord,
  listBucketFiles,
  selectRecords,
  selectRecordsWithFilter,
  signInWithEmailAndPassword,
  signOutUser,
  signUpWithEmailAndPassword,
  updateRecords,
  uploadFileToBucket,
  upsertRecord,
} from "./supabaseHelpers";

describe("supabase helpers", () => {
  let mockTableClient: ReturnType<typeof createMockTableClient>;
  let mockStorageClient: ReturnType<typeof createMockStorageClient>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockTableClient = createMockTableClient();
    mockStorageClient = createMockStorageClient();
    const supabaseMocks = getSupabaseMock();
    supabaseMocks.from.mockReturnValue(mockTableClient);
    supabaseMocks.storage.from.mockReturnValue(mockStorageClient);
  });

  it("signs up, signs in and signs out", async () => {
    const supabaseMocks = getSupabaseMock();
    const signUpResponse = { data: null, error: null };
    supabaseMocks.auth.signUp.mockResolvedValue(signUpResponse);
    const signInResponse = { data: null, error: null };
    supabaseMocks.auth.signInWithPassword.mockResolvedValue(signInResponse);
    const signOutResponse = { data: null, error: null };
    supabaseMocks.auth.signOut.mockResolvedValue(signOutResponse);

    const signUpResult = await signUpWithEmailAndPassword("test@ribif.com", "pass");
    expect(supabaseMocks.auth.signUp).toHaveBeenCalledWith({ email: "test@ribif.com", password: "pass" });
    expect(signUpResult).toBe(signUpResponse);

    const signInResult = await signInWithEmailAndPassword("test@ribif.com", "pass");
    expect(supabaseMocks.auth.signInWithPassword).toHaveBeenCalledWith({ email: "test@ribif.com", password: "pass" });
    expect(signInResult).toBe(signInResponse);

    const signOutResult = await signOutUser();
    expect(supabaseMocks.auth.signOut).toHaveBeenCalled();
    expect(signOutResult).toBe(signOutResponse);
  });

  it("manages storage buckets", async () => {
    const supabaseMocks = getSupabaseMock();
    const bucketResponse = { data: null, error: null };
    supabaseMocks.storage.createBucket.mockResolvedValue(bucketResponse);
    await createStorageBucket("uploads", { public: false });
    expect(supabaseMocks.storage.createBucket).toHaveBeenCalledWith("uploads", { public: false });

    const fakeFile = { name: "plan.dxf" } as File;
    await uploadFileToBucket("uploads", "layout/plan.dxf", fakeFile, { upsert: true });
    expect(supabaseMocks.storage.from).toHaveBeenCalledWith("uploads");
    expect(mockStorageClient.upload).toHaveBeenCalledWith("layout/plan.dxf", fakeFile, { upsert: true });

    await listBucketFiles("uploads", "layout", { limit: 6 });
    expect(mockStorageClient.list).toHaveBeenCalledWith("layout", { limit: 6 });
  });

  it("inserts and upserts records", async () => {
    const supabaseMocks = getSupabaseMock();
    await insertRecord("machines", { name: "Extrudeuse" });
    expect(supabaseMocks.from).toHaveBeenCalledWith("machines");
    expect(mockTableClient.insert).toHaveBeenCalledWith({ name: "Extrudeuse" });

    await upsertRecord("machines", { id: 1, name: "Extrudeuse", active: true }, { onConflict: "id" });
    expect(mockTableClient.upsert).toHaveBeenCalledWith({ id: 1, name: "Extrudeuse", active: true }, { onConflict: "id" });
  });

  it("updates, deletes and selects records", async () => {
    await updateRecords("machines", { active: false }, { id: 10 });
    expect(mockTableClient.update).toHaveBeenCalledWith({ active: false });
    expect(mockTableClient.match).toHaveBeenCalledWith({ id: 10 });

    await deleteRecords("machines", { id: 5 });
    expect(mockTableClient.delete).toHaveBeenCalled();
    expect(mockTableClient.match).toHaveBeenCalledWith({ id: 5 });

    await selectRecords("machines");
    expect(mockTableClient.select).toHaveBeenCalledWith("*");

    await selectRecordsWithFilter("machines", "name", "Pression");
    expect(mockTableClient.select).toHaveBeenCalledWith("*");
    expect(mockTableClient.eq).toHaveBeenCalledWith("name", "Pression");
  });
});
