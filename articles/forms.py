from django import forms
from tinymce.widgets import TinyMCE

from .models import Article, ArticleCategory, ArticleComment


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


_INPUT = (
    "width:100%;border:1.5px solid #e2e8f0;border-radius:10px;"
    "padding:12px 14px;font-size:14px;outline:none;box-sizing:border-box;"
    "transition:border-color .18s,box-shadow .18s;"
)


class CommentForm(forms.ModelForm):
    class Meta:
        model = ArticleComment
        fields = ["name", "email", "comment"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Your name",
                "required": True,
                "style": _INPUT,
                "onfocus": "this.style.borderColor='#0B7A4B';this.style.boxShadow='0 0 0 3px rgba(11,122,75,.1)'",
                "onblur": "this.style.borderColor='#e2e8f0';this.style.boxShadow='none'",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "your@email.com (optional)",
                "style": _INPUT,
                "onfocus": "this.style.borderColor='#0B7A4B';this.style.boxShadow='0 0 0 3px rgba(11,122,75,.1)'",
                "onblur": "this.style.borderColor='#e2e8f0';this.style.boxShadow='none'",
            }),
            "comment": forms.Textarea(attrs={
                "placeholder": "Share your thoughts…",
                "rows": 4,
                "maxlength": 2000,
                "required": True,
                "style": _INPUT + "resize:vertical;",
                "onfocus": "this.style.borderColor='#0B7A4B';this.style.boxShadow='0 0 0 3px rgba(11,122,75,.1)'",
                "onblur": "this.style.borderColor='#e2e8f0';this.style.boxShadow='none'",
            }),
        }


class ReplyForm(forms.Form):
    reply = forms.CharField(
        max_length=2000,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Write your reply…",
            "class": "w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm focus:border-green-400 focus:outline-none focus:ring-2 focus:ring-green-100",
        }),
    )
