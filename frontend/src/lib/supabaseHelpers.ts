import { supabase } from "./supabaseClient";

type MatchRecord = Record<string, string | number | boolean>;
type StorageOptions = {
  cacheControl?: string;
  upsert?: boolean;
  contentType?: string;
};

export const signUpWithEmailAndPassword = (email: string, password: string) =>
  supabase.auth.signUp({ email, password });

export const signInWithEmailAndPassword = (email: string, password: string) =>
  supabase.auth.signInWithPassword({ email, password });

export const signOutUser = () => supabase.auth.signOut();

export const createStorageBucket = (bucketName: string, options?: { public: boolean }) =>
  supabase.storage.createBucket(bucketName, options ?? { public: false });

export const uploadFileToBucket = (
  bucketName: string,
  destinationPath: string,
  file: File | Blob | Buffer | ArrayBuffer,
  options?: StorageOptions
) => supabase.storage.from(bucketName).upload(destinationPath, file, options);

export const listBucketFiles = (
  bucketName: string,
  path = "",
  options?: { limit?: number; offset?: number }
) => supabase.storage.from(bucketName).list(path, options);

export const insertRecord = <T extends Record<string, unknown>>(table: string, payload: T) =>
  supabase.from(table).insert(payload);

export const upsertRecord = <T extends Record<string, unknown>>(
  table: string,
  payload: T,
  options?: { onConflict?: string; ignoreDuplicates?: boolean }
) => supabase.from(table).upsert(payload, options);

export const updateRecords = <T extends Record<string, unknown>>(
  table: string,
  updates: T,
  match: MatchRecord
) => supabase.from(table).update(updates).match(match);

export const deleteRecords = (table: string, match: MatchRecord) =>
  supabase.from(table).delete().match(match);

export const selectRecords = (table: string, columns = "*") =>
  supabase.from(table).select(columns);

export const selectRecordsWithFilter = (
  table: string,
  filterColumn: string,
  value: string | number,
  columns = "*"
) => supabase.from(table).select(columns).eq(filterColumn, value);
