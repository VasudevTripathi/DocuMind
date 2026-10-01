export const INITIAL_DOCUMENTS = [
  {
    id: 'doc-1',
    name: 'Attention Is All You Need.pdf',
    type: 'PDF',
    size: '2.4 MB',
    sizeBytes: 2516582,
    uploadedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    modifiedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    status: 'analyzed',
    category: 'Research Paper'
  },
  {
    id: 'doc-2',
    name: 'Annual Report 2023.pdf',
    type: 'PDF',
    size: '4.1 MB',
    sizeBytes: 4300000,
    uploadedAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    modifiedAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    status: 'analyzed',
    category: 'Business Report'
  },
  {
    id: 'doc-3',
    name: 'Technical Specification.docx',
    type: 'DOCX',
    size: '1.2 MB',
    sizeBytes: 1258291,
    uploadedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    modifiedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'processing',
    category: 'Technical'
  },
  {
    id: 'doc-4',
    name: 'Contract Agreement.pdf',
    type: 'PDF',
    size: '3.8 MB',
    sizeBytes: 3984588,
    uploadedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    modifiedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'analyzed',
    category: 'Legal'
  }
];
