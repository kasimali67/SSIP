"use client";

import { useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { useRouter } from "next/navigation";
import { Camera, Loader2, UploadCloud } from "lucide-react";

import { ConfidenceField } from "@/components/civic/ConfidenceField";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { extractOcr } from "@/lib/api";
import { savePendingFields, toLast4 } from "@/lib/verificationStore";

interface VerificationFields {
  name: string;
  dob: string;
  idNumber: string;
}

type FieldKey = keyof VerificationFields;

export function DocumentUpload() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fields, setFields] = useState<VerificationFields | null>(null);
  const [confidences, setConfidences] = useState<Record<FieldKey, number> | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  function selectFile(nextFile: File) {
    setFile(nextFile);
    setFields(null);
    setConfidences(null);
    setError(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(
      nextFile.type.startsWith("image/")
        ? URL.createObjectURL(nextFile)
        : null,
    );
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const dropped = event.dataTransfer.files.item(0);
    if (dropped) {
      selectFile(dropped);
    }
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.item(0);
    if (chosen) {
      selectFile(chosen);
    }
    event.target.value = "";
  }

  async function handleExtract() {
    if (!file) {
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const result = await extractOcr(file);
      setFields({
        name: result.name.value ?? "",
        dob: result.dob.value ?? "",
        idNumber: result.id_number.value ?? "",
      });
      setConfidences({
        name: result.name.confidence,
        dob: result.dob.confidence,
        idNumber: result.id_number.confidence,
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Extraction failed.");
    } finally {
      setLoading(false);
    }
  }

  function updateField(key: FieldKey, value: string) {
    setFields((current) => (current ? { ...current, [key]: value } : current));
  }

  function handleConfirm() {
    if (!fields || !confidences) {
      return;
    }
    savePendingFields({
      name: { value: fields.name, confidence: confidences.name },
      dob: { value: fields.dob, confidence: confidences.dob },
      id_last4: {
        value: toLast4(fields.idNumber),
        confidence: confidences.idNumber,
      },
    });
    router.push("/verify");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Document OCR</CardTitle>
        <CardDescription>
          Upload a document image to extract the Name, Date of Birth, and ID
          number.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div
          role="button"
          tabIndex={0}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              fileInputRef.current?.click();
            }
          }}
          onDragOver={(event) => event.preventDefault()}
          onDrop={handleDrop}
          className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors hover:border-primary"
        >
          <UploadCloud className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm font-medium">
            Drag and drop an image here, or click to browse
          </p>
          <p className="text-xs text-muted-foreground">PNG or JPG</p>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleInputChange}
        />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={handleInputChange}
        />

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => cameraInputRef.current?.click()}
          >
            <Camera className="h-4 w-4" />
            Use camera
          </Button>
          <Button
            type="button"
            onClick={handleExtract}
            disabled={!file || loading}
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Extract fields
          </Button>
        </div>

        {previewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={previewUrl}
            alt="Selected document preview"
            className="max-h-64 w-full rounded-md border object-contain"
          />
        ) : null}

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        {fields && confidences ? (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold">Verify extracted fields</h2>
            <ConfidenceField
              id="name"
              labelKey="fields.name"
              value={fields.name}
              confidence={confidences.name}
              onChange={(value) => updateField("name", value)}
            />
            <ConfidenceField
              id="dob"
              labelKey="fields.dob"
              value={fields.dob}
              confidence={confidences.dob}
              onChange={(value) => updateField("dob", value)}
            />
            <ConfidenceField
              id="idNumber"
              labelKey="fields.idLast4"
              value={fields.idNumber}
              confidence={confidences.idNumber}
              inputMode="numeric"
              onChange={(value) => updateField("idNumber", value)}
            />
            <Button type="button" onClick={handleConfirm}>
              Confirm &amp; Save
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
