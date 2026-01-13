import { useForm } from '@tanstack/react-form';
import { zodValidator } from '@tanstack/zod-form-adapter';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Field,
    FieldError,
    FieldLabel,
} from '@/components/ui/field';

import type { Member } from '@/types/member';

interface AddMemberFormProps {
    onClose: () => void;
    initialData?: Member | null;
}

const memberSchema = z.object({
    firstName: z.string().min(1, 'First name is required'),
    lastName: z.string().min(1, 'Last name is required'),
});

export default function AddMemberForm({ onClose, initialData }: AddMemberFormProps) {
    const form = useForm({
        defaultValues: {
            firstName: initialData ? initialData.name.split(' ')[0] : '',
            lastName: initialData ? initialData.name.split(' ').slice(1).join(' ') : '',
        },
        // @ts-ignore
        validatorAdapter: zodValidator(),
        onSubmit: async ({ value }) => {
            console.log('Form Submitted:', value);
            onClose();
        },
    });

    return (
        <form
            onSubmit={(e) => {
                e.preventDefault();
                e.stopPropagation();
                form.handleSubmit();
            }}
            className="flex flex-col h-full"
        >
            <div className="space-y-4 flex-1">
                <form.Field
                    name="firstName"
                    validators={{
                        onChange: memberSchema.shape.firstName,
                    }}
                    children={(field) => {
                        return (
                            <Field className="space-y-2">
                                <FieldLabel htmlFor={field.name}>First Name</FieldLabel>
                                <Input
                                    id={field.name}
                                    name={field.name}
                                    value={field.state.value}
                                    onBlur={field.handleBlur}
                                    onChange={(e) => field.handleChange(e.target.value)}
                                    placeholder="e.g., Sohel"
                                />
                                <FieldError errors={field.state.meta.errors} />
                            </Field>
                        );
                    }}
                />

                <form.Field
                    name="lastName"
                    validators={{
                        onChange: memberSchema.shape.lastName,
                    }}
                    children={(field) => {
                        return (
                            <Field className="space-y-2">
                                <FieldLabel htmlFor={field.name}>Last Name</FieldLabel>
                                <Input
                                    id={field.name}
                                    name={field.name}
                                    value={field.state.value}
                                    onBlur={field.handleBlur}
                                    onChange={(e) => field.handleChange(e.target.value)}
                                    placeholder="e.g., Khan"
                                />
                                <FieldError errors={field.state.meta.errors} />
                            </Field>
                        );
                    }}
                />
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t border-gray-100 mt-6">
                <Button variant="ghost" type="button" onClick={onClose} className="hover:bg-gray-100">
                    Cancel
                </Button>
                <Button type="submit" className="bg-[#2a75ff] hover:bg-[#1d5dd9] text-white">
                    Submit
                </Button>
            </div>
        </form>
    );
}
