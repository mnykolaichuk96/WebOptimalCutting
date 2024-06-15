from django import forms


class ManualCuttingForm(forms.Form):
    raw_length = forms.FloatField(label='Długość surowca')
    parts_length = forms.CharField(widget=forms.HiddenInput(), required=False)
    parts_quantity = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean(self):
        cleaned_data = super().clean()
        parts_length = self.data.getlist('parts_length[]')
        parts_quantity = self.data.getlist('parts_quantity[]')

        # Ensure that the lengths and quantities are properly paired
        if len(parts_length) != len(parts_quantity):
            raise forms.ValidationError("Lengths and quantities must have the same number of elements.")

        # Check that all lengths and quantities are provided
        if not parts_length or not parts_quantity:
            raise forms.ValidationError("Both parts_length and parts_quantity are required.")

        # Check that all lengths and quantities are valid integers
        try:
            parts_length = [int(length) for length in parts_length]
            parts_quantity = [int(quantity) for quantity in parts_quantity]
        except ValueError:
            raise forms.ValidationError("All parts_length and parts_quantity must be valid integers.")

        cleaned_data['parts_length'] = parts_length
        cleaned_data['parts_quantity'] = parts_quantity
        return cleaned_data


class FileCuttingForm(forms.Form):
    parts_file = forms.FileField(label='Upload Parts File', required=True)