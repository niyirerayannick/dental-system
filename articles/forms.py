from django import forms
from tinymce.widgets import TinyMCE

from .models import Article, ArticleCategory


class ArticleForm(forms.ModelForm):
    content = forms.CharField(
        widget=TinyMCE(),
        label="Content",
    )

    class Meta:
        model = Article
        fields = [
            "title",
            "category",
            "excerpt",
            "content",
            "featured_image",
            "video_url",
            "is_published",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm focus:border-green-400 focus:outline-none focus:ring-2 focus:ring-green-100",
                "placeholder": "Article title",
            }),
            "category": forms.Select(attrs={
                "class": "w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm focus:border-green-400 focus:outline-none focus:ring-2 focus:ring-green-100",
            }),
            "excerpt": forms.Textarea(attrs={
                "class": "w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm focus:border-green-400 focus:outline-none focus:ring-2 focus:ring-green-100",
                "rows": 3,
                "placeholder": "Short summary shown on listing cards (max 400 chars)",
                "maxlength": 400,
            }),
            "featured_image": forms.ClearableFileInput(attrs={
                "class": "w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm focus:border-green-400 focus:outline-none focus:ring-2 focus:ring-green-100",
                "accept": "image/*",
            }),
            "video_url": forms.URLInput(attrs={
                "class": "w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm focus:border-green-400 focus:outline-none focus:ring-2 focus:ring-green-100",
                "placeholder": "https://www.youtube.com/embed/... or Spotify embed URL",
            }),
            "is_published": forms.CheckboxInput(attrs={
                "class": "h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500",
            }),
        }
