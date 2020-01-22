import re, sys
patterns = {
    '[àáảãạăắằẵặẳâầấậẫẩ]': 'a',
    '[đ]': 'd',
    '[èéẻẽẹêềếểễệ]': 'e',
    '[ìíỉĩị]': 'i',
    '[òóỏõọôồốổỗộơờớởỡợ]': 'o',
    '[ùúủũụưừứửữự]': 'u',
    '[ỳýỷỹỵ]': 'y'
}
def tiengVietKhongDau(text):
    """
    Converts from 'Tiếng Việt có dấu' to 'Tieng Viet khong dau'
    https://sangnd.wordpress.com/2014/01/03/python-chuyen-tieng-viet-co-dau-thanh-khong-dau/
    """
    for regex, replace in patterns.items():
        text = re.sub(regex, replace, text)
        # deal with upper-cases
        text = re.sub(regex.upper(), replace.upper(), text)
    return text
