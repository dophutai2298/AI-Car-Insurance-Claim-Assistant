# Third-Party Software Notices

This project uses third-party open-source software.

## Required private package download

The `deepdoc_vietocr` wheel is required for the local DeepDoc document-analysis
integration. The wheel is intentionally excluded from Git and must be downloaded
before installing the backend dependencies.

- Package: `deepdoc_vietocr-0.1.0-py3-none-any.whl`
- Download [here](https://drive.google.com/file/d/1LBGigUwhSzncbh4uMpkq5kZzU1JETlQz/view?usp=sharing)
- Install location: `backend/package/`

After downloading the wheel, install it from the backend virtual environment:

```bash
pip install package/deepdoc_vietocr-0.1.0-py3-none-any.whl
```

## DeepDoc / RAGFlow

Parts of `deepdoc_vietocr` are derived from DeepDoc, part of the RAGFlow project.

- Project: RAGFlow / DeepDoc
- Copyright: InfiniFlow Authors
- License: Apache License 2.0
- Source: https://github.com/infiniflow/ragflow

## VietOCR

Vietnamese text recognition functionality uses VietOCR.

- Project: VietOCR
- Copyright: VietOCR contributors
- License: Apache License 2.0
- Source: https://github.com/pbcquoc/vietocr

## deepdoc_vietocr

The application uses a customized `deepdoc_vietocr` package that integrates DeepDoc components with VietOCR for Vietnamese document processing.

The package retains the applicable copyright and license notices of its upstream components.
