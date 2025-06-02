from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    # Можно переопределить поле рейтинга для отображения звезд
    rating = forms.ChoiceField(
        choices=Review.RATING_OPTIONS,
        widget=forms.RadioSelect,  # отобразит в виде радио-кнопок, которые можно стилизовать под звезды
        label='Оценка'
    )

    class Meta:
        model = Review
        fields = ['rating', 'text', 'image']
