
import mimetypes
import os

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden


def serve_protected_file(request, file_field, as_attachment=False, filename=None):
    """
    Serve a file protected by server-level blocking (e.g., .htaccess).
    
    Args:
        request: The Django request object (unused currently but good for future extension).
        file_field: The FileField/ImageField containing the file to serve.
        as_attachment (bool): If True, force download. If False, try to display inline (preview).
        filename (str): Optional custom filename for the download.
    
    Returns:
        FileResponse: The streaming file response.
    
    Raises:
        Http404: If the file does not exist.
    """
    if not file_field or not file_field.name:
        raise Http404("File not found.")

    # Get the absolute path to the file
    try:
        file_path = file_field.path
    except NotImplementedError:
        # Handle cases where storage doesn't support path (e.g. cloud storage)
        # This implementation assumes local FileSystemStorage as per requirements
        raise Http404("File storage not supported for local serving.")

    if not os.path.exists(file_path):
        raise Http404("File does not exist on server.")

    # Open the file in binary mode
    # FileResponse closes the file automatically
    response = FileResponse(open(file_path, 'rb'))
    
    # Set Content-Type
    content_type, encoding = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'application/octet-stream'
    response['Content-Type'] = content_type
    
    # Set Content-Disposition
    if not filename:
        filename = os.path.basename(file_path)
        
    disposition_type = 'attachment' if as_attachment else 'inline'
    response['Content-Disposition'] = f'{disposition_type}; filename="{filename}"'

    return response
