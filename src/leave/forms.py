from django import forms
from .models import Leave
import datetime

class LeaveCreationForm(forms.ModelForm):
	reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 4, 'cols': 40}))
	class Meta:
		model = Leave
		exclude = ['user','defaultdays','hrcomments','status','is_approved','updated','created']



	def clean_enddate(self):
		enddate = self.cleaned_data['enddate']
		startdate = self.cleaned_data['startdate']
		today_date = datetime.date.today()

		if (startdate or enddate) < today_date:# both dates must not be in the past
			raise forms.ValidationError("Selected dates are incorrect,please select again")

		elif startdate >= enddate:# TRUE -> FUTURE DATE > PAST DATE,FALSE other wise
			raise forms.ValidationError("Selected dates are wrong")

		return enddate


class LeaveAdminForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = '__all__'

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.is_approved:
            instance.status = 'approved'
            instance.is_rejected = False
        elif instance.is_rejected:
            instance.status = 'rejected'
            instance.is_approved = False
        else:
            instance.status = 'pending'
        if commit:
            instance.save()
        return instance
            

