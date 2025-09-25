import re
from typing import List, Dict, Any, Optional

class SSMLBuilder:
    """SSML 생성 클래스"""
    
    def build_ssml_with_marks(
        self, 
        text: str, 
        lang_code: str, 
        mark_prefix: str,
        punctuation_pause_ms: Optional[Dict[str, int]] = None
    ) -> str:
        """주어진 텍스트에 단어별 mark 태그와 문장 부호에 따른 break 태그를 삽입하여 SSML을 생성합니다."""
        if not text or not text.strip():
            return ""

        # XML/SSML에 영향을 줄 수 있는 문자를 이스케이프 처리
        processed_text = text.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # <break> 태그를 추가할 문장 부호 주위에 공백을 추가하여 토큰으로 분리되도록 함
        if punctuation_pause_ms:
            for punc in punctuation_pause_ms.keys():
                processed_text = processed_text.replace(punc, f' {punc} ')
        
        tokens = processed_text.split()
        num_tokens = len(tokens)
        body_parts = []
        word_counter = 0

        for i, token in enumerate(tokens):
            is_last_token = (i == num_tokens - 1)

            if punctuation_pause_ms and token in punctuation_pause_ms:
                # 토큰이 정지 시간을 추가할 문장 부호인 경우
                if not body_parts:
                    # 문장 부호가 맨 앞에 오는 경우
                    body_parts.append(token)
                else:
                    # 이전 파트에 문장 부호 추가
                    prev_part = body_parts[-1]
                    if not is_last_token:
                        duration_ms = punctuation_pause_ms[token]
                        body_parts[-1] = f'{prev_part}{token}<break time="{duration_ms}ms"/>'
                    else:
                        # 마지막 토큰이면 break 없이 문장 부호만 추가
                        body_parts[-1] = f'{prev_part}{token}'
            else:
                # 일반 단어인 경우, mark 태그 추가
                mark_name = f"{mark_prefix}_{word_counter}"
                body_parts.append(f'{token} <mark name="{mark_name}"/>')
                word_counter += 1
        
        ssml_body = ' '.join(body_parts)

        full_ssml = f'''<?xml version="1.0" encoding="UTF-8"?>
<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="{lang_code}">
    {ssml_body.strip()}
</speak>'''
        return full_ssml