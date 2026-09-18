"use client";

import { useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { Camera, Loader2, TriangleAlert, UploadCloud } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { extractOcr } from "@/lib/api";

const LOW_CONFIDENCE_THRESHOLD = 0.75;

interface VerificationFields {
  name: string;
  dob: string;
  idNumber: string;
}

type FieldKey = keyof VerificationFields;

interface VerificationFieldProps {
  id: string;
  label: string;
  value: string;
  confidence: number;
  onChange: (value: string) => void;
}

function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

function VerificationField({
  id,
  label,
  value,
  confidence,
  onChange,
}: VerificationFieldProps) {
  const isLowConfidence = confidence < LOW_CONFIDENCE_THRESHOLD;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label htmlFor={id}>{label}</Label>
        <Badge variant={isLowConfidence ? "warning" : "secondary"}>
          {isLowConfidence ? <TriangleAlert className="h-3 w-3" /> : null}
          {formatConfidence(confidence)}
        </Badge>
      </div>
      <Input
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={
          isLowConfidence
            ? "border-orange-400 focus-visible:ring-orange-400"
            : undefined
        }
      />
      {isLowConfidence ? (
        <p className="flex items-center gap-1 text-xs text-orange-600">
          <TriangleAlert className="h-3 w-3" />
          Low confidence — please verify this value.
        </p>
      ) : null}
    </div>
  );
}

export function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fields, setFields] = useState<VerificationFields | null>(null);
  const [confidences, setConfidences] = useState<Record<FieldKey, number> | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  function selectFile(nextFile: File) {
    setFile(nextFile);
    setFields(null);
    setConfidences(null);
    setSaved(false);
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
    if (!fields) {
      return;
    }
    console.log("Confirmed extraction", {
      name: fields.name,
      dob: fields.dob,
      idNumber: fields.idNumber,
    });
    setSaved(true);
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
            <VerificationField
              id="name"
              label="Name"
              value={fields.name}
              confidence={confidences.name}
              onChange={(value) => updateField("name", value)}
            />
            <VerificationField
              id="dob"
              label="Date of Birth"
              value={fields.dob}
              confidence={confidences.dob}
              onChange={(value) => updateField("dob", value)}
            />
            <VerificationField
              id="idNumber"
              label="ID Number"
              value={fields.idNumber}
              confidence={confidences.idNumber}
              onChange={(value) => updateField("idNumber", value)}
            />
            <div className="flex items-center gap-3">
              <Button type="button" onClick={handleConfirm}>
                Confirm &amp; Save
              </Button>
              {saved ? (
                <span className="text-sm text-muted-foreground">
                  Saved to console.
                </span>
              ) : null}
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
