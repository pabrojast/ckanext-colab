# Images Directory

This directory contains images for the CKAN Colab extension.

## Required Images

### colab.jpg
- **Location**: `ckanext/colab/public/colab_static/images/colab.jpg`
- **Purpose**: Background image for the Data Contributor Portal banner
- **Recommended size**: 1200x400 pixels or similar landscape format
- **Format**: JPG
- **Description**: This image will be used as the background for the portal banner with an overlay

## Usage

The image is referenced in the template as:
```html
<div class="section-title-bg" style="background-image: url('/colab_static/images/colab.jpg');"></div>
```

## Fallback

If the image is not available, a gradient fallback will be used:
```css
background: linear-gradient(135deg, #0077d4 0%, #004c8c 100%);
``` 