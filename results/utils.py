import os
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings

def generate_winner_poster(template_path, program, winners, fest_name="FestAlchemy", config=None):
    """
    Generates a winner poster using PILLOW.
    template_path: Path to the template image file.
    program: Program model instance.
    winners: List of Result objects (already sorted by rank).
    config: Dictionary with field positions and sizes.
    """
    POSTER_W = 1080
    POSTER_H = 1350

    # Load template image or create fallback
    if template_path:
        try:
            img = Image.open(template_path).convert('RGBA')
            img = img.resize((POSTER_W, POSTER_H), Image.LANCZOS)
        except Exception:
            img = Image.new('RGBA', (POSTER_W, POSTER_H), (20, 20, 40, 255))
    else:
        img = Image.new('RGBA', (POSTER_W, POSTER_H), (20, 20, 40, 255))
    
    draw = ImageDraw.Draw(img)

    # Default config if none provided
    if not config:
        from programs.models import default_poster_config
        config = default_poster_config()

    def get_font(key, size, family='Inter', weight=None):
        # Determine weight based on key to match frontend (800 for titles/names, 600 for categories/teams)
        if not weight:
            is_bold = (key == 'program' or key.endswith('_name'))
            weight = 'ExtraBold' if is_bold else 'SemiBold'
        
        # Strip space from family name (e.g. 'Playfair Display' -> 'PlayfairDisplay')
        filename_family = family.replace(' ', '')
        font_names = [
            f"{filename_family}-{weight}.ttf",
            f"{filename_family}-Regular.ttf",
            f"Inter-{weight}.ttf",
            "Inter-Regular.ttf",
        ]
            
        for name in font_names:
            font_path = os.path.join(settings.MEDIA_ROOT, 'fonts', name)
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    pass
        
        # System font paths for fallback
        system_paths = [
            "C:\\Windows\\Fonts\\arialbd.ttf" if (weight == 'ExtraBold') else "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if (weight == 'ExtraBold') else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        for p in system_paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def hex_to_rgba(hex_str):
        hex_str = hex_str.lstrip('#')
        if len(hex_str) == 6:
            r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
            return (r, g, b, 255)
        return (255, 255, 255, 255)

    def draw_text(key, text):
        """Draw text at configured position (percentage or absolute pixels)."""
        field = config.get(key)
        if not field or not text:
            return
        if field.get('hidden', False):
            return
            
        x_val = field.get('x', 540)
        y_val = field.get('y', 675)
        font_size = field.get('size', 40)
        color = field.get('color', '#ffffff')
        align = field.get('align', 'center')
        family = field.get('font', 'Inter')
        weight = field.get('weight')

        # Determine if percentage or pixel based coordinates
        if x_val <= 100 and y_val <= 100:
            px = int(x_val / 100.0 * POSTER_W)
            py = int(y_val / 100.0 * POSTER_H)
            scaled_size = int(font_size * POSTER_W / 1000.0)
        else:
            px = int(x_val)
            py = int(y_val)
            scaled_size = int(font_size)

        font = get_font(key, scaled_size, family=family, weight=weight)
        fill = hex_to_rgba(color)

        # Determine Pillow anchor based on alignment (lm=left-middle, mm=middle-middle, rm=right-middle)
        anchor_val = "mm"
        if align == "left":
            anchor_val = "lm"
        elif align == "right":
            anchor_val = "rm"

        # Draw centered or aligned text with manual fallback
        try:
            draw.text((px, py), text, font=font, fill=fill, anchor=anchor_val)
        except Exception:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            if align == "left":
                draw.text((px, py - th // 2), text, font=font, fill=fill)
            elif align == "right":
                draw.text((px - tw, py - th // 2), text, font=font, fill=fill)
            else:
                draw.text((px - tw // 2, py - th // 2), text, font=font, fill=fill)

    # Draw content
    draw_text('program', program.name)
    draw_text('category', program.category.name if program.category else '')

    for i, res in enumerate(winners[:3], start=1):
        rank_label_text = config.get(f'rank{i}_label', {}).get('text', f'{i}st' if i==1 else f'{i}nd' if i==2 else f'{i}rd')
        draw_text(f'rank{i}_label', rank_label_text)
        draw_text(f'rank{i}_name', res.member.name)
        draw_text(f'rank{i}_team', res.member.team.name if res.member.team else '')

    # Draw result label and dynamic result value
    result_label_text = config.get('result_label', {}).get('text', 'Result No:')
    draw_text('result_label', result_label_text)
    draw_text('result_value', str(program.id))

    return img


def recalculate_team_points():
    """Recalculate total points and breakdown for all teams based on published results."""
    from participants.models import Team
    from results.models import TeamPoints, Result
    from django.db.models import Sum

    # Reset all team points to 0
    TeamPoints.objects.all().update(total_points=0, breakdown={})

    for team in Team.objects.all():
        # Get all published results for this team's members
        published_results = Result.objects.filter(member__team=team, published=True)
        
        # Calculate total points
        total = published_results.aggregate(total=Sum('points'))['total'] or 0.0
        
        # Build breakdown dictionary
        breakdown = {}
        for r in published_results:
            prog_name = r.program.name
            if prog_name not in breakdown:
                breakdown[prog_name] = []
            breakdown[prog_name].append({
                'member': r.member.name,
                'rank': r.rank,
                'pts': r.points
            })
        
        # Update or create the TeamPoints record
        tp, created = TeamPoints.objects.get_or_create(team=team)
        tp.total_points = int(total)
        tp.breakdown = breakdown
        tp.save()

